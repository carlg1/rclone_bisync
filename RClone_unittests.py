#!/usr/bin/python3

#################################################################################
## Imports
#################################################################################
import json
import unittest
from RClone import rclone, parsetime


class RClone__parse_lsjson(unittest.TestCase):
    def test__parse_lsjson(self):
        rc = rclone('local', 'remote')

        orgdata = [
            {"Path" : "file1", "Name" : "file1", "Size" : 374, "MimeType" : "application/epub+zip",     "ModTime" : "2017-12-20T22:44:06.44Z",      "IsDir": False, "Hashes" : {"MD5":"36f26ef6284358d4c89fdf8eeaa7f9f1"},"ID":"1d2hBAuERpcCKUi_N1cre4JNvF3purJBH"},
            {"Path" : "file2", "Name" : "file2", "Size" : 200, "MimeType" : "application/octet-stream", "ModTime" : "2017-12-20T18:38:49.46-07:00", "IsDir": False, "Hashes" : {"DropboxHash":"7283dd95ef7d712aa812815ea3c550212b03f14e8b32c5c04d9cecfd71e109d1","MD5":"fcf568928af294b37caa868c8cca2bf3","QuickXorHash":"84c9c0969da606c489af7c673a305759c1b0c3b5","SHA-1":"d38317c41580763d67d1a8ee1f383b25e6ebc6fe"}},
        ]
        tstres = {
            "file1" : {'size' : 374, 'time' : "2017-12-20 15:44:06.440000", 'md5sum' : "36f26ef6284358d4c89fdf8eeaa7f9f1"},
            "file2" : {'size' : 200, 'time' : "2017-12-20 18:38:49.460000", 'md5sum' : "fcf568928af294b37caa868c8cca2bf3"},
        }

        bdata = json.dumps(orgdata).encode('utf-8')
        res = rc._parse_lsjson(bdata, 'local')

        self.assertEqual(res, tstres)

class RClone_parsetime(unittest.TestCase):
    def test_parsetime_local(self):
        dt = "2018-07-22T20:54:59.696878795-06:00"
        t = parsetime(dt)
        self.assertEqual("2018-07-22 20:54:59.696878", t)

    def test_parsetime_remote(self):
        dt = "2018-01-02T19:44:06.533Z"
        t = parsetime(dt)
        self.assertEqual("2018-01-02 12:44:06.533000", t)

    def test_parsetime_previous(self):
        dt = "2018-07-22 23:20:30.472000"
        t = parsetime(dt)
        self.assertEqual("2018-07-22 23:20:30.472000", t)

    def test_parsetime_previous2(self):
        dt = "2018-07-22 23:20:30.47"
        t = parsetime(dt)
        self.assertEqual("2018-07-22 23:20:30.470000", t)

    def test_parsetime_tzchange(self):
        dt = "2018-07-23T02:55:00.18Z"
        res = "2018-07-22 20:55:00.180000"
        t = parsetime(dt)
        self.assertEqual(res, t)

    def test_parsetime_weird_tz(self):
        dt = "2018-07-22T20:54:58.696878795-06:01"
        t = parsetime(dt)
        self.assertEqual("2018-07-22 20:55:58.696878", t)

    def test_parsetime_nousecs(self):
        dt = "2019-09-17T20:24:46-06:00"
        t = parsetime(dt)
        self.assertEqual("2019-09-17 20:24:46.000000", t)

if(__name__ == '__main__'):
    unittest.main()

