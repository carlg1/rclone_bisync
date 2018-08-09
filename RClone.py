#!/usr/bin/python3

#################################################################################
## Imports
#################################################################################
import re
import json
import subprocess
from enum import Enum, IntFlag
from datetime import datetime, timezone


#################################################################################
## 'Constants'
#################################################################################
RCLONE = "rclone"


#################################################################################
## Enums
#################################################################################
class Direction(IntFlag):
    neither = 0
    local = 1
    remote = 2
    both = 3

class Action(Enum):
    none = 0
    copyto = 1
    deletefrom = 2
    conflict = 3


#################################################################################
## parsetime helper function
#################################################################################
def parsetime(dtstr):
    tz = None
    tzp = "%z"
    x = re.split(r'[ T:.-]', dtstr)

    if('Z' in x[6]):
        x[6] = x[6][:-1]
        tz = "+0000"

    if(len(x[6]) > 6):
        x[6] = x[6][:6]
    elif(len(x[6]) < 6):
        x[6] += "0" * (6 - len(x[6]))

    if(len(x) > 7):
        if('+' in dtstr):
            tz = '+' + x[7]
        else:
            tz = '-' + x[7]
        if(len(x) > 8):
            tz += x[8]
    elif(not tz):
        tz = datetime.now(timezone.utc).astimezone().tzinfo
        tzp = "%Z"

    x = [int(i) for i in x[:7]]

    dstr = "%04d-%02d-%02d %02d:%02d:%02d.%06d%s" % (*x[:7], tz)
    dt = datetime.strptime(dstr, "%Y-%m-%d %H:%M:%S.%f" + tzp)

    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f")


#################################################################################
### RClone Class
#################################################################################
class rclone():
    def __init__(self, local, remote, googledocs=False, dryrun=False):
        self.local = local
        self.remote = remote
        self.gdocs = googledocs
        self.dryrun = dryrun

    def __str__(self):
        t = {'local': self.local, 'remote': self.remote, 'gdocs': self.gdocs, 'dryrun': self.dryrun}
        return str(t)

    def lsjson(self, direction, includegdocs=False):
        if(direction == Direction.local):
            target = self.local
        elif(direction == Direction.remote):
            target = self.remote
        else:
            raise ValueError("Invalid direction arg")

        cmd = [RCLONE, "lsjson", "--hash", "--recursive", target]
        rv = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        return self._parse_lsjson(rv.stdout, target)

    def lsl(self, direction, includegdocs=False):
        if(direction == Direction.local):
            target = self.local
        elif(direction == Direction.remote):
            target = self.remote
        else:
            raise ValueError("Invalid direction arg")
        
        cmd = [RCLONE, "lsl", target]
        if(not includegdocs):
            cmd.insert(1, "--drive-skip-gdocs")

        rv = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        return self._parse_lsl(rv.stdout)

    def md5sum(self, direction, includegdocs=False):
        if(direction == Direction.local):
            target = self.local
        elif(direction == Direction.remote):
            target = self.remote
        else:
            raise ValueError("Invalid direction arg")

        cmd = [RCLONE, "md5sum", target]
        if(includegdocs):
            cmd.insert(1, "--drive-skip-gdocs")

        rv = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return self._parse_md5sum(rv.stdout)

    def sync(self, direction):
        if(direction == Direction.local):
            source = self.remote
            target = self.local
        elif(direction == Direction.remote):
            source = self.local
            target = self.remote
        else:
            raise ValueError("Invalid direction arg")

        cmd = [RCLONE, "sync", source, target]
        if(self.dryrun):
            cmd.insert(1, "--dry-run")
        if(not self.gdocs):
            cmd.insert(1, "--drive-skip-gdocs")

        rv = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def copyto(self, name, direction):
        if(direction == Direction.local):
            source = self.remote
            target = self.local
        elif(direction == Direction.remote):
            source = self.local
            target = self.remote
        else:
            raise ValueError("Invalid direction arg")

        source += "/" + name
        target += "/" + name
        
        cmd = [RCLONE, "copyto", source, target]
        if(self.dryrun):
            cmd.insert(1, "--dry-run")
        if(not self.gdocs):
            cmd.insert(1, "--drive-skip-gdocs")

        print("cmd = '%s'" % (" ".join(cmd)))
        rv = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self._dumpoutput("STDOUT:", rv.stdout)
        self._dumpoutput("STDERR:", rv.stderr)

    def delete(self, name, direction):
        if(direction == Direction.local):
            target = self.local
        elif(direction == Direction.remote):
            target = self.remote
        else:
            raise ValueError("Invalid direction arg")

        target += "/" + name
        
        cmd = [RCLONE, "delete", target]
        if(self.dryrun):
            cmd.insert(1, "--dry-run")
        if(not self.gdocs):
            cmd.insert(1, "--drive-skip-gdocs")

        print("cmd = '%s'" % (" ".join(cmd)))
        rv = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self._dumpoutput("STDOUT:", rv.stdout)
        self._dumpoutput("STDERR:", rv.stderr)

    def _parse_lsl(self, pipe):
        lsl = {}
        for l in pipe.split(b'\n'):
            listres = l.split(maxsplit=3)

            if(len(listres) == 0):
                continue
            if(len(listres) < 4):
                raise

            flist = {}

            flist['size'] = listres[0].decode('ascii')
            flist['time'] = listres[1].decode('ascii') + " " + listres[2].decode('ascii')
            name = listres[3].decode('utf-8')
            lsl[name] = flist

        return lsl

    def _parse_lsjson(self, pipe, target):
        lsj = {}
        j = json.loads(pipe)

        for f in j:
            if(f['IsDir']):
                continue

            n = f['Path']
            lsj[n] = {}

            lsj[n]['size'] = f['Size']
            lsj[n]['time'] = parsetime(f['ModTime'])

            if('Hashes' in f):
                lsj[n]['md5sum'] = f['Hashes']['MD5']
            else:
                lsj[n]['md5sum'] = None

            if(target == self.remote):
                if('openxmlformats' in f['MimeType']):
                    lsj[n]['gdoc'] = True
                else:
                    lsj[n]['gdoc'] = False

        return lsj

    def _parse_md5sum(self, pipe):
        md5list = {}
        for l in pipe.split(b'\n'):
            res = l.split(maxsplit=1)

            if(len(res) == 0):
                continue

            name = res[1].decode('utf-8')
            if(name in md5list):
                raise

            md5list[name] = res[0].decode('ascii')

        return md5list

    def _dumpoutput(self, title, pipe):
        print(title)
        for l in pipe.split(b'\n'):
            print(l.decode('utf-8'))


#################################################################################
## main
#################################################################################
if(__name__ == '__main__'):
    pass
