#!/usr/bin/env python
# xfail-license

import sys, fileinput, subprocess, re, argparse, os
from licenseck import *

err=0
cols=100

# Be careful to support Python 2.4, 2.6, and 3.x here!
config_proc=subprocess.Popen([ "git", "config", "core.autocrlf" ],
                             stdout=subprocess.PIPE)
result=config_proc.communicate()[0]

true="true".encode('utf8')
autocrlf=result.strip() == true if result is not None else False

def report_error_name_no(name, no, s):
    global err
    print("%s:%d: %s" % (name, no, s))
    err=1

def report_err(s):
    report_error_name_no(fileinput.filename(), fileinput.filelineno(), s)

def report_warn(s):
    print("%s:%d: %s" % (fileinput.filename(),
                         fileinput.filelineno(),
                         s))

def do_license_check(name, contents):
    if not check_license(name, contents):
        report_error_name_no(name, 1, "incorrect license")

parser = argparse.ArgumentParser(description='Tidy source files.')
parser.add_argument('--srcdir')
args = parser.parse_args()

file_names = []
for (dirpath, dirnames, filenames) in os.walk(os.path.join(args.srcdir, 'src')):
    for name in filenames:
        if name.endswith("_gen.rs") or ".#" in name:
            continue
        def in_dir(d):
            return dirpath.startswith(os.path.join(args.srcdir, d))
        def add():
            file_names.append(os.path.join(dirpath, name))
        ext = os.path.splitext(name)[1]
        if ext in ['.rs', '.rc'] and not in_dir('src/test'):
            add()
        elif ext in ['.py'] and in_dir('src/etc'):
            add()
        elif ext in ['.c', '.cpp', '.h']:
            if in_dir('src/rt/jemalloc') or in_dir('src/rt/linenoise') \
                    or in_dir('src/rt/vg') or in_dir('src/rt/msvc'):
                continue
            if in_dir('src/rt') or in_dir('src/rustllvm'):
                if name != 'miniz.cpp':
                    add()

current_name = ""
current_contents = ""

try:
    for line in fileinput.input(file_names,
                                openhook=fileinput.hook_encoded("utf-8")):

        if fileinput.filename().find("tidy.py") == -1:
            if line.find("FIXME") != -1:
                if re.search("FIXME.*#\d+", line) == None:
                    report_err("FIXME without issue number")
            if line.find("TODO") != -1:
                report_err("TODO is deprecated; use FIXME")
            match = re.match(r'^.*//\s*(NOTE.*)$', line)
            if match:
                report_warn(match.group(1))
        if (line.find('\t') != -1 and
            fileinput.filename().find("Makefile") == -1):
            report_err("tab character")
        if not autocrlf and line.find('\r') != -1:
            report_err("CR character")
        if line.endswith(" \n") or line.endswith("\t\n"):
            report_err("trailing whitespace")
        line_len = len(line)-2 if autocrlf else len(line)-1

        if line_len > cols:
            report_err("line longer than %d chars" % cols)

        if fileinput.isfirstline() and current_name != "":
            do_license_check(current_name, current_contents)

        if fileinput.isfirstline():
            current_name = fileinput.filename()
            current_contents = ""

        current_contents += line

    if current_name != "":
        do_license_check(current_name, current_contents)

except UnicodeDecodeError, e:
    report_err("UTF-8 decoding error " + str(e))


sys.exit(err)
