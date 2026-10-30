#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Preserve GNU tar's configure probes, generate headers, export sources to Meson.

This is a deliberately limited reader of configure-produced Automake metadata,
not a make implementation. Only BUILT_SOURCES header recipes are evaluated;
compilation, archiving, linking, scheduling and installation belong to Meson.
No make executable is invoked. Unexpected recipe constructs fail explicitly.
"""
import argparse, hashlib, json, os, pathlib, re, shlex, shutil, subprocess, sys

class Metadata:
    def __init__(self, path):
        text=path.read_text().replace('\\\n',' ')
        self.variables={}; self.rules={}; current=[]
        for line in text.splitlines():
            if line.startswith('#'): continue
            m=re.match(r'^([\w.]+)\s*(\+?=)\s*(.*)$',line)
            if m:
                key,op,value=m.groups()
                self.variables[key]=(self.variables.get(key,'')+' '+value) if op=='+=' else value
                current=[]
            elif line.startswith('\t'):
                for target in current:self.rules[target][1].append(line[1:])
            elif line and not line[0].isspace() and ':' in line and '=' not in line.split(':',1)[0]:
                targets,deps=line.split(':',1);current=targets.split()
                for target in current:self.rules[target]=(deps,[])
            elif line.strip(): current=[]
        # Suppress Automake's display-only prefix macros.
        for name in ['AM_V_GEN','AM_V_at','gl_V_at','AM_V_P']:self.variables[name]=''
    def expand(self,text):
        for _ in range(100):
            def variable(match):
                if any(c.isspace() for c in match[1]) or ':' in match[1]:
                    raise RuntimeError('unsupported make function in header metadata: '+match[1])
                return self.variables.get(match[1],'')
            changed=re.sub(r'\$\(([^()]+)\)',variable,text)
            if changed==text:
                if '$(' in text:raise RuntimeError('unsupported metadata expansion: '+text)
                return text
            text=changed
        raise RuntimeError('recursive metadata variable')
    def get(self,name):return self.expand(self.variables.get(name,''))
    def headers(self,src,build):
        for name in self.get('BUILT_SOURCES').split():
            if (src/name).exists():continue # Generated parser shipped in release.
            if not name.endswith('.h'):raise RuntimeError('unexpected generated source: '+name)
            if name not in self.rules:raise RuntimeError('missing header recipe: '+name)
            deps,commands=self.rules[name]
            (build/name).parent.mkdir(parents=True,exist_ok=True)
            expanded_deps=self.expand(deps).split()
            first=expanded_deps[0] if expanded_deps else ''
            if first and not pathlib.Path(first).is_absolute() and (src/first).exists():first=str(src/first)
            for command in commands:
                command=self.expand(command).replace('$@',shlex.quote(name)).replace('$<',shlex.quote(first)).replace('$$','$')
                command=command.lstrip('@')
                if re.search(r'\b(?:make|gmake|cc|gcc|clang|ar|ranlib)\b',command.split(';')[0]) and 'sed' not in command:
                    raise RuntimeError('non-header recipe refused: '+command)
                subprocess.run(['/bin/sh','-ec',command],cwd=build,check=True)

p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--build',required=True)
p.add_argument('--cc',default='cc');p.add_argument('--cflags',default='');p.add_argument('--ldflags',default='')
p.add_argument('--prefix',default='/usr/local');p.add_argument('--bindir',default='/usr/local/bin');p.add_argument('--libdir',default='/usr/local/lib');p.add_argument('--libexecdir',default='/usr/local/libexec');p.add_argument('--localedir',default='/usr/local/share/locale')
p.add_argument('--acl',default='auto');p.add_argument('--selinux',default='auto');p.add_argument('--nls',default='true');p.add_argument('--xattrs',default='true');p.add_argument('--rmt',default='true');p.add_argument('--gzip',default='gzip');p.add_argument('--archive',default='-');p.add_argument('--blocking',default='20');p.add_argument('--query')
a=p.parse_args();src=pathlib.Path(a.source).resolve();root=pathlib.Path(a.build).resolve();cfg=root/'gnulib-config';manifest=cfg/'meson-metadata.json'
if a.query:
    data=json.loads(manifest.read_text());print('\n'.join(data[a.query]));sys.exit(0)
if not sys.platform.startswith('linux'):raise SystemExit('This Meson port currently supports native Linux builds.')
inputs=[src/'configure',src/'config.h.in',
        *(src/d/'Makefile.in' for d in ['gnu','lib','src','tests']),
        *sorted((src/'gnu').rglob('*.h')),
        *sorted((src/'lib').glob('*.in.h')),
        src/'gnu/malloc/dynarray-skeleton.c',src/'tests/atlocal.in',
        pathlib.Path(__file__).resolve()]
fingerprint=hashlib.sha256(json.dumps(vars(a),sort_keys=True).encode())
for file in inputs:fingerprint.update(file.read_bytes())
stamp=cfg/'meson-fingerprint'
if manifest.exists() and stamp.exists() and stamp.read_text()==fingerprint.hexdigest():
    cached=json.loads(manifest.read_text())
    if all(pathlib.Path(x).exists() for x in cached.get('generated_headers',[])) and cached.get('generated_headers'):sys.exit(0)
cfg.mkdir(parents=True,exist_ok=True)
args=[str(src/'configure'),'--disable-gcc-warnings','--disable-dependency-tracking',f'--prefix={a.prefix}',f'--bindir={a.bindir}',f'--libdir={a.libdir}',f'--libexecdir={a.libexecdir}',f'--localedir={a.localedir}',f'--with-gzip={a.gzip}']
if a.acl=='disabled':args+=['--disable-acl','--without-posix-acls']
if a.selinux=='disabled':args+=['--without-selinux']
if a.nls=='false':args+=['--disable-nls']
if a.xattrs=='false':args+=['--without-xattrs']
if a.rmt=='false':args+=[f'--with-rmt={a.libexecdir}/rmt']
env=os.environ.copy();env.update(CC=a.cc,CFLAGS=a.cflags,CPPFLAGS='',LDFLAGS=a.ldflags,FORCE_UNSAFE_CONFIGURE='1',DEFAULT_ARCHIVE=a.archive,DEFAULT_BLOCKING=a.blocking,MAKE='true',ac_cv_prog_make_true_set='yes',am_cv_make_support_nested_variables='yes')
with (cfg/'configure-output.log').open('w') as log:
    result=subprocess.run(args,cwd=cfg,env=env,stdout=log,stderr=subprocess.STDOUT)
if result.returncode:
    sys.stderr.write((cfg/'configure-output.log').read_text()[-12000:]);raise SystemExit(result.returncode)
data={}
for directory,var in [('gnu','libgnu_a_SOURCES'),('lib','libtar_a_SOURCES'),('src','tar_SOURCES')]:
    m=Metadata(cfg/directory/'Makefile');m.headers(src/directory,cfg/directory)
    names=m.get(var).split()
    if directory=='gnu':names += [n[:-2]+'.c' for n in m.get('gl_LIBOBJS').split()]
    if directory=='gnu':names=[n[:-2]+'.c' if n.endswith('.y') else n for n in names]
    data[directory]=list(dict.fromkeys(str(src/directory/n) for n in names if n.endswith('.c')))
    for name in data[directory]:
        if not pathlib.Path(name).is_file():raise RuntimeError('missing configured source: '+name)
m=Metadata(cfg/'src/Makefile')
flags=m.get('tar_LDADD')+' '+m.get('LIBINTL')+' '+m.get('LIBICONV')
if a.acl=='enabled' and not re.search(r'^#define USE_ACL 1$',(cfg/'config.h').read_text(),re.M):
    raise RuntimeError('ACL support requested but configure could not enable it')
if a.selinux=='enabled' and not m.get('LIB_SELINUX').strip():
    raise RuntimeError('SELinux support requested but configure could not enable it')
data['link_args']=[x for x in shlex.split(flags) if x.startswith(('-l','-L','-Wl,','-pthread'))]
data['inputs']=[str(x) for x in inputs]
# Mirror only generated headers into Meson's normal build/source include pairs.
data['generated_headers']=[]
shutil.copyfile(cfg/'config.log',root/'config.log')
for header in [cfg/'config.h',*sorted((cfg/'gnu').rglob('*.h')),*sorted((cfg/'lib').rglob('*.h'))]:
    dest=root/header.relative_to(cfg);dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists() or dest.read_bytes()!=header.read_bytes():shutil.copyfile(header,dest)
    data['generated_headers'].append(str(dest))
# Autotest runs directly from Meson's tests directory with Meson-built helpers.
(root/'tests').mkdir(exist_ok=True)
for name in ['atconfig','atlocal']:
    text=(cfg/'tests'/name).read_text().replace(str(cfg),str(root))
    (root/'tests'/name).write_text(text)
if a.nls=='true':
    data['translations']=[str(x) for x in sorted((src/'po').glob('*.gmo'))]
else:data['translations']=[]
manifest.write_text(json.dumps(data,indent=2)+'\n');stamp.write_text(fingerprint.hexdigest())
