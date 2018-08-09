#!/usr/bin/python3

#################################################################################
## Imports
#################################################################################
import io
import os
import sys
import json
import argparse
from enum import Enum
from xdg.BaseDirectory import xdg_config_home

import RClone


#################################################################################
## TODO
#################################################################################
# Better google doc handling
# handle dup file names
# use sync to copy files 1 dir
# other meta data?
# renamed files


#################################################################################
## 'Constants'
#################################################################################
NAME = "rclone_bisync"
VERSION = "0.0.1"


#################################################################################
## Global Vars
#################################################################################
files = {}
config = {}
rclone = None


#################################################################################
## Enums
#################################################################################


#################################################################################
## Remote File Code
#################################################################################
def VersionAsInt():
    ver = VERSION.split(".")
    return int(ver[0]) * 10000 + int(ver[1]) * 100 + int(ver[2])


#################################################################################
## Remote File Code
#################################################################################
def get_remote_list():
    rlist = rclone.lsjson(RClone.Direction.remote, includegdocs=True)

    for name in rlist:
        if(name not in files):
            files[name] = {}
        files[name]['remote'] = rlist[name]


#################################################################################
## Local File Code
#################################################################################
def get_local_list():
    llist = rclone.lsjson(RClone.Direction.local)

    for name in llist:
        if(name not in files):
            files[name] = {}
        files[name]['local'] = llist[name]


#################################################################################
## Previous File Code
#################################################################################
def get_previous_list():
    try:
        with open(config['prevfile'], "r") as f:
            plist = json.load(f)

        if(plist['version'] != VersionAsInt()):
            print("Previous file is of an old unsupported version!")
            sys.exit(1)

        f = plist['files']
        for name in f:
            files[name] = {}
            files[name]['previous'] = {}
            files[name]['previous']['size'] = int(f[name]['previous']['size'])
            files[name]['previous']['time'] = RClone.parsetime(f[name]['previous']['time'])
            files[name]['previous']['rtime'] = RClone.parsetime(f[name]['previous']['rtime'])
            files[name]['previous']['md5sum'] = f[name]['previous']['md5sum']

    except FileNotFoundError:
        print("Missing previous file (%s), you will have to re-run the initial sync!" % config['prevfile'])
        sys.exit(1)                
    except json.JSONDecodeError:
        print("Previous file (%s) is corrupt!" % config['prevfile'])
        sys.exit(1)                
    except KeyError:
        print("Previous file (%s) is missing a key!" % config['prevfile'])
        print(name)
        print(files[name])
        sys.exit(1)


#################################################################################
## Calculate Diffs & Actions
#################################################################################
def calc_diffs(f):
    cf = {}
    tests = ((0, 1), (0, 2)) #0=Previous, 1=Local, 2=Remote; so compare Prev to Curr, Prev to Remote
    lookups = ('previous', 'local', 'remote')

    for name in f:
        vals = ('previous' in f[name], 'local' in f[name], 'remote' in f[name])

        if(vals[2] and f[name]['remote']['gdoc']): #fix me -- google doc work
            continue

        if(False in vals):
            f[name]['missing'] = True

        for test in tests:
            T1 = vals[test[0]]
            T2 = vals[test[1]]
            L1 = lookups[test[0]]
            L2 = lookups[test[1]]

            if(T1 and T2):
                if(f[name][L1]['md5sum'] != f[name][L2]['md5sum']):
                    f[name]['changed'] = 'md5sum'
                    if('which' not in f[name]):
                        f[name]['which'] = RClone.Direction.neither
                    f[name]['which'] |= test[1]
                    continue

                if(f[name][L1]['size'] != f[name][L2]['size']):
                    f[name]['changed'] = 'size'
                    if('which' not in f[name]):
                        f[name]['which'] = RClone.Direction.neither
                    f[name]['which'] |= test[1]
                    continue

        if('changed' not in f[name]):
            w = 0
            if(vals[0] and vals[1] and f[name]['previous']['time'] != f[name]['local']['time']):
                f[name]['changed'] = 'time'
                w += 1 #copy to remote
            if(vals[0] and vals[2] and f[name]['previous']['rtime'] != f[name]['remote']['time']):
                f[name]['changed'] = 'time'
                w += 2 #copy to local
            if(w):
                f[name]['which'] = w

        if('changed' in f[name] or 'missing' in f[name]):
            cf[name] = calc_actions(f[name])

    return cf

def calc_actions(f):
    #fix deal w/ time vs rtime diffs
    cf = {}
    m = {}
    c = {}

    if('changed' in f):
        w = f['which']
        if(w == RClone.Direction.local):
            c['action'] = RClone.Action.copyto
            c['direction'] = RClone.Direction.remote
        elif(w == RClone.Direction.remote):
            c['action'] = RClone.Action.copyto
            c['direction'] = RClone.Direction.local
        elif(w == RClone.Direction.both):
            c['action'] = RClone.Action.conflict
            c['direction'] = RClone.Direction.neither
        else:
            raise RuntimeError("A file is marked as changed incorrectly -- time")

    if('missing' in f):
        P = 'previous' in f
        L = 'local' in f
        R = 'remote' in f

        if((P == False and L == False and R == False) or
           (P == True  and L == True  and R == True)):
            #not valid cases as the file is present in all 3 or missing from a 3
            #If this happens it is a bug somewhere else in the code
            raise RuntimeError("A file is marked as missing incorrectly")
        elif(P == True and L == False and R == False):
            # Deleted manually? still nothing to do
            m['action'] = RClone.Action.none
            m['direction'] = RClone.Direction.neither
        elif(P == False and L == True and R == True):
            # File manually added? still nothing to do
            m['action'] = RClone.Action.none
            m['direction'] = RClone.Direction.neither
        elif(P == False and L == True and R == False):
            # New local file
            m['action'] = RClone.Action.copyto
            m['direction'] = RClone.Direction.remote 
        elif(P == True  and L == True  and R == False):
            # Deleted from the cloud
            m['action'] = RClone.Action.deletefrom
            m['direction'] = RClone.Direction.local
        elif(P == False and L == False and R == True):
            # New file in cloud
            m['action'] = RClone.Action.copyto
            m['direction'] = RClone.Direction.local
        elif(P == True and L == False and R == True):
            # Deleted from the local copy
            m['action'] = RClone.Action.deletefrom
            m['direction'] = RClone.Direction.remote

    if(c):
        return c
    elif(m):
        return m
    else:
        raise RuntimeError("A file is marked as changed/missing incorrectly")


#################################################################################
## Run1stSync
#################################################################################
def Run1stSync():
    localdirexisted = False

    if(os.path.isdir(config["local"])):
        localdirexisted = True
    else:
        os.mkdir(config["local"])

    if(config['1stsync'] == "remote"):
        # sync from the cloud
        direction = RClone.Direction.local
        if(localdirexisted):
            get_local_list()
            if(files):
                print("Unable to sync from remote due to non-empty local dir")
                sys.exit(1)

    elif(config['1stsync'] == "local"):
        get_remote_list()
        direction = RClone.Direction.remote
        if(files):
            print("Unable to sync to remote due to non-empty cloud")
            sys.exit(1)

    rclone.sync(direction)


#################################################################################
## RunSync
#################################################################################
def RunSync():
    get_previous_list()
    get_local_list()
    get_remote_list()

    changed_files = calc_diffs(files)

    for name in changed_files:
        print("File: '%s' needs to be %s on %s" % (name, str(changed_files[name]['action']), str(changed_files[name]['direction'])))
        if(changed_files[name]['direction'] == RClone.Direction.neither):
            print("    --> %s " % str(files[name]))

    if(config['dryrun']):
        return

    if(not changed_files):
        return

    x = input("Make the above changes? ")
    x = x.lower()
    if(x != "yes" and x != "y"):
        print("Quiting and not applying changes")
        sys.exit(0)

    for name in changed_files:
        if(changed_files[name]['action'] == RClone.Action.copyto):
            rclone.copyto(name, changed_files[name]['direction'])
        elif(changed_files[name]['action'] == RClone.Action.deletefrom):
            rclone.delete(name, changed_files[name]['direction'])


#################################################################################
## ParseArgs
#################################################################################
def ParseArgs():
    initmsg = "required and only allowed on initial sync"
    
    desc = "This program utilizes rclone to preform a bi-directional sync."
    parser = argparse.ArgumentParser(description=desc, allow_abbrev=False)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-P', '--profile', help="Name of the profile to be loaded to sync")
    group.add_argument(      '--configfile', help="load this config file instead of one specified by profile")

    parser.add_argument(      '--dry-run', action='store_true', help="Will not preform any actions (passes --dry-run to rclone)")

    parser.add_argument(      '--initsync', choices=["remote", "local"], help="Location the initial sync will use as the source") #, "merge"
    parser.add_argument(      '--local', help="Local path for the sync [%s]" % initmsg)
    parser.add_argument(      '--remote', help="Rclone remote for the sync [%s]" % initmsg)
    parser.add_argument(      '--google-docs', action='store_true', help="Pulls down Google Docs, they are ignored by default [%s]" % initmsg)
    #-v --verbose
    #--extra-rclone-args
    #rclode verbose

    args = parser.parse_args()

    if(args.configfile):
        config["conffile"] = args.configfile
    else:
        config["conffile"] = "/".join([xdg_config_home, NAME, args.profile])

    config['1stsync'] = args.initsync
    config['dryrun'] = args.dry_run

    if(config['1stsync']):
        config['local'] = args.local
        config['remote'] = args.remote
        config['gdocs'] = args.google_docs

        if(not config['local']):
            parser.error("Miising required argument for initial sync --local")
        if(not config['remote']):
            parser.error("Miising required argument for initial sync --remote")


#################################################################################
## ReadConfigFile
#################################################################################
def ReadConfigFile():
    configexits = os.path.isfile(config["conffile"])

    if(config['1stsync'] and configexits):
        print("'%s' config file exists please remove it and rerun" % config["conffile"])
        sys.exit(1)
    if(not config['1stsync'] and not configexits):
        print("'%s' config file doesn't exists please run --initsync 1st" % config["conffile"])
        sys.exit(1)

    try:
        configpath = os.path.dirname(config["conffile"])
        os.mkdir(configpath)
    except FileExistsError:
        pass

    if(not os.access(configpath, os.W_OK)):
        print("'%s' is not writable please resolve and rerun" % config["conffile"])
        sys.exit(1)
    
    if(not config['1stsync']):
        with open(config["conffile"], "r") as f:
            try:
                jsonconfig = json.load(f)
            except json.JSONDecodeError:
                print("'%s' config file is corrupt" % config["conffile"])
                sys.exit(1)                

        config['local']    = jsonconfig['local']
        config['remote']   = jsonconfig['remote']
        config['gdocs']    = jsonconfig['gdocs']
        config['prevfile'] = jsonconfig['prevfile']
        config['version']  = jsonconfig['version']
    else:
        config['prevfile'] = config["conffile"] + ".previous"


#################################################################################
## HandleConfigWrite
#################################################################################
def WriteConfigFile():
    jsonconfig = {}
    jsonconfig['local']    = config['local']
    jsonconfig['remote']   = config['remote']
    jsonconfig['gdocs']    = config['gdocs']
    jsonconfig['prevfile'] = config['prevfile']
    jsonconfig['version']  = VersionAsInt()

    with open(config["conffile"], "w") as f:
        json.dump(jsonconfig, f, indent=4, separators=(',', ': '))


#################################################################################
## Initialize
#################################################################################
def Initialize():
    global rclone

    ParseArgs()
    ReadConfigFile()

    rclone = RClone.rclone(config['local'], config['remote'], config['gdocs'], config['dryrun'])


#################################################################################
## CleanUp
#################################################################################
def CleanUp():
    if(not config['dryrun']):
        #get ready to create 'previous' for next sync
        global files
        files = {}

        get_local_list()
        get_remote_list()
        for name in list(files): #note -- missing gdoc file names
            if('remote' in files[name] and files[name]['remote']['gdoc']):
                del(files[name])
                continue
            files[name]['previous'] = files[name]['local']
            files[name]['previous']['rtime'] = files[name]['remote']['time']
            del(files[name]['local'])
            del(files[name]['remote'])

        j = {}
        j['files'] = files
        j['version'] = VersionAsInt()
        
        with open(config['prevfile'], "w") as f:
            json.dump(j, f, indent=4, separators=(',', ': '))


#################################################################################
## main
#################################################################################
if(__name__ == '__main__'):
    Initialize()

    if(config['1stsync']):
        Run1stSync()
        WriteConfigFile()
    else:
        RunSync()

    CleanUp()
