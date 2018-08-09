#!/usr/bin/python3

#################################################################################
## Imports
#################################################################################
import unittest
import copy

from rclone_bisync import *

class TestCalcActions(unittest.TestCase):
    maxDiff = None
    def test_calc_actions_not_missing_or_changed(self):
        """
        This tests that if the missing flag and changed flag are missing (ie the file isn't missing/changed).
        Results: Exception thrown
        """
        f = {}

        with self.assertRaises(RuntimeError):
            cf = calc_actions(f)

    def test_calc_actions_missing_plr(self):
        """
        This tests the file is not being found in previous, local, and remote.
        Results: Exception thrown
        """
        f = {'missing' : True}
        with self.assertRaises(RuntimeError):
            cf = calc_actions(f)

    def test_calc_actions_missing_Plr(self):
        """
        This tests the file is not being found in local, and remote, but is found in previous.
        Results: Nothing should happen
        """
        f = {'missing' : True, 'previous' : True}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.none, 'direction' : RClone.Direction.neither})

    def test_calc_actions_missing_pLr(self):
        """
        This tests the file is not being found in previous, and remote, but is found in local.
        Results: copy the file to remote (Upload)
        """
        f = {'missing' : True, 'local' : True}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.remote})

    def test_calc_actions_missing_PLr(self):
        """
        This tests the file is not being found in remote, but is found in previous, and local.
        Results: delete local
        """
        f = {'missing' : True, 'previous' : True, 'local' : True}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.deletefrom, 'direction' : RClone.Direction.local})

    def test_calc_actions_missing_plR(self):
        """
        This tests the file is not being found in previous, and local, but is found in remote.
        Results: copy the file to local (Download)
        """
        f = {'missing' : True, 'remote' : {'gdoc' : False}}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.local})

    def test_calc_actions_missing_PlR(self):
        """
        This tests the file is not being found in local, but is found in previous, and remote.
        Results: delete remote
        """
        f = {'missing' : True, 'previous' : True, 'remote' : {'gdoc' : False}}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.deletefrom, 'direction' : RClone.Direction.remote})

    def test_calc_actions_missing_pLR(self):
        """
        This tests the file is not being found in previous, but is found in local, and remote.
        Results: Nothing should happen
        """
        f = {'missing' : True, 'local' : True, 'remote' : {'gdoc' : False}}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.none, 'direction' : RClone.Direction.neither})

    def test_calc_actions_missing_PLR(self):
        """
        This tests the file being found in previous, local, and remote.
        Results: Exception thrown
        """
        f = {'missing' : True, 'remote' : {'gdoc' : False},
                       'local' : True, 'previous' : True}
        with self.assertRaises(RuntimeError):
            cf = calc_actions(f)

    def test_calc_actions_changed_time_lr(self):
        """
        This tests the file not being modified (but being reported as such -- really a bug somewhere else and should raise an exception)
        Results: Nothing should happen
        """
        f = {'changed' : 'time', 'which' : 0,
             'remote' : {'time' : '12345', 'gdoc' : False},
             'local' : {'time' : '12345'},
             'previous' : {'time' : '12345', 'rtime' : '12345'}}

        with self.assertRaises(RuntimeError):
            cf = calc_actions(f)

    def test_calc_actions_changed_time_Lr(self):
        """
        This tests the Local file modified and the remote not.
        Results: Copy the local file to the Cloud (Upload)
        """
        f = {'changed' : 'time', 'which' : 1, 'remote' : {'time' : '12345'},
                       'local' : {'time' : '12346'}, 'previous' : {'time' : '12345'}}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.remote})

    def test_calc_actions_changed_time_lR(self):
        """
        This tests the Local file is not modified and the remote is.
        Results: Copy the Cload file to local (download)
        """
        f = {'changed' : 'time', 'which' : 2, 'remote' : {'time' : '12346'},
                       'local' : {'time' : '12345'}, 'previous' : {'time' : '12345'}}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.local})

    def test_calc_actions_changed_time_LR(self):
        """
        This tests the Local file and remote files are both modified.
        Results: The files are in conflict
        """
        f = {'changed' : 'time', 'which' : 3, 'remote' : {'time' : '12346'}, 'local' : {'time' : '12345'}, 'previous' : {'time' : '12344'}}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.conflict, 'direction' : RClone.Direction.neither})

    def test_calc_actions_changed_size_lr(self):
        """
        This tests the file not being modified (but being reported as such -- really a bug somewhere else and should raise an exception)
        Results: Nothing should happen
        """
        f = {'changed' : 'size', 'which' : 0,
             'remote' : {'size' : '12345', 'gdoc' : False},
             'local' : {'size' : '12345'},
             'previous' : {'size' : '12345'}}

        with self.assertRaises(RuntimeError):
            cf = calc_actions(f)

    def test_calc_actions_changed_size_Lr(self):
        """
        This tests the Local file modified and the remote not.
        Results: Copy the local file to the Cloud (Upload)
        """
        f = {'changed' : 'size', 'which' : 1,
             'remote' : {'size' : '12345'},
             'local' : {'size' : '12346'},
             'previous' : {'size' : '12345'}}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.remote})

    def test_calc_actions_changed_size_lR(self):
        """
        This tests the Local file is not modified and the remote is.
        Results: Copy the Cload file to local (download)
        """
        f = {'changed' : 'size', 'which' : 2,
             'remote' : {'size' : '12346'},
             'local' : {'size' : '12345'},
             'previous' : {'size' : '12345'}}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.local})

    def test_calc_actions_changed_size_LR(self):
        """
        This tests the Local file and remote files are both modified.
        Results: The files are in conflict
        """
        f = {'changed' : 'size', 'which' : 3, 'remote' : {'size' : '12346'}, 'local' : {'size' : '12345'}, 'previous' : {'size' : '12344'}}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.conflict, 'direction' : RClone.Direction.neither})

    def test_calc_actions_changed_missing(self):
        """
        This tests the 
        Results: 
        """
        f = {'changed' : 'size', 'which' : 1, 'missing' : True,
             'local' : {'size' : '12345'}, 'previous' : {'size' : '12344'}}

        cf = calc_actions(f)
        self.assertEqual(cf, {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.remote})

class TestCalcDiffs(unittest.TestCase):
    maxDiff = None
    def test_calc_diffs_pCR_missing(self):
        """
        This tests if a file is marked as missing correctly (Previous missing)
        Results: f[name]['missing'] == True
        """
        f = {'file1': {'remote': {'md5sum': "1", 'time': "2", 'size': 3, 'gdoc': False},
                       'local': {'md5sum': "1", 'time': "2", 'size': 3}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)

        org['file1']['missing'] = True
        self.assertEqual(f, org)
        self.assertEqual(cf, {'file1' : {'action' : RClone.Action.none, 'direction' : RClone.Direction.neither}})

    def test_calc_diffs_PlR_missing(self):
        """
        This tests if a file is marked as missing correctly (Local missing)
        Results: f[name]['missing'] == True
        """
        f = {'file2': {'remote': {'md5sum': "1", 'time': "2", 'size': 3, 'gdoc': False},
                       'previous': {'md5sum': "1", 'time': "2", 'size': 3, 'rtime': "2"}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)

        org['file2']['missing'] = True
        self.assertEqual(f, org)
        self.assertEqual(cf, {'file2' : {'action' : RClone.Action.deletefrom, 'direction' : RClone.Direction.remote}})

    def test_calc_diffs_PLr_missing(self):
        """
        This tests if a file is marked as missing correctly (Remote missing)
        Results: f[name]['missing'] == True
        """
        f = {'file3': {'local': {'md5sum': "1", 'time': "2", 'size': 3},
                       'previous': {'md5sum': "1", 'time': "2", 'size': 3}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)

        org['file3']['missing'] = True
        self.assertEqual(f, org)
        self.assertEqual(cf, {'file3' : {'action' : RClone.Action.deletefrom, 'direction' : RClone.Direction.local}})

    def test_calc_diffs_plr_missing(self):
        """
        This tests if a file is marked as missing correctly (all missing -- exception will be thrown later)
        Results: f[name]['missing'] == True
        """
        f = {'file4': {}}
        org = copy.deepcopy(f)

        with self.assertRaises(RuntimeError):
            cf = calc_diffs(f)

    def test_calc_diffs_PLR_not_missing(self):
        """
        This tests if a file is marked as missing correctly (none missing -- exception will be thrown later)
        Results: f == original f
        """
        f = {'file5': {'local': {'md5sum': "1", 'time': "2", 'size': 3},
                       'previous': {'md5sum': "1", 'time': "2", 'size': 3, 'rtime': "2"},
                       'remote': {'md5sum': "1", 'time': "2", 'size': 3, 'gdoc': False}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)
        self.assertEqual(f, org)
        self.assertEqual(cf, {})

    def test_calc_diffs_changed_L(self):
        """
        This tests if a file is marked as changed correctly (Local changed)
        Results: f[name]['changed'] == md5sum
        """
        f = {'file6': {'local': {'md5sum': "10", 'time': "2", 'size': 3},
                       'previous': {'md5sum': "1", 'time': "2", 'size': 3},
                       'remote': {'md5sum': "1", 'time': "2", 'size': 3, 'gdoc': False}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)

        org['file6']['changed'] = 'md5sum'
        org['file6']['which'] = 1
        self.assertEqual(f, org)
        self.assertEqual(cf, {'file6' : {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.remote}})

    def test_calc_diffs_changed_R(self):
        """
        This tests if a file is marked as changed correctly (Remote Changed)
        Results: f[name]['changed'] == 'md5sum'
        """
        f = {'file7': {'local': {'md5sum': "1", 'time': "2", 'size': 3},
                       'previous': {'md5sum': "1", 'time': "2", 'size': 3},
                       'remote': {'md5sum': "10", 'time': "2", 'size': 3, 'gdoc': False}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)

        org['file7']['changed'] = 'md5sum'
        org['file7']['which'] = 2
        self.assertEqual(f, org)
        self.assertEqual(cf, {'file7' : {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.local}})

    def test_calc_diffs_changed_LR(self):
        """
        This tests if a file is marked as changed correctly (Local & Remote Changed)
        Results: f[name]['changed'] == 'md5sum'
        """
        f = {'file8': {'local': {'md5sum': "11", 'time': "2", 'size': 3},
                       'previous': {'md5sum': "1", 'time': "2", 'size': 3},
                       'remote': {'md5sum': "10", 'time': "2", 'size': 3, 'gdoc': False}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)

        org['file8']['changed'] = 'md5sum'
        org['file8']['which'] = 3
        self.assertEqual(f, org)
        self.assertEqual(cf, {'file8' : {'action' : RClone.Action.conflict, 'direction' : RClone.Direction.neither}})

    def test_calc_diffs_changed_L_time(self):
        """
        This tests if a file is marked as changed correctly (Local Changed)
        Results: f[name]['changed'] == 'time'
        """
        f = {'file9': {'local': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000001", 'size': 3},
                       'previous': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 3, 'rtime': "2017-12-20 15:43:27.776000001"},
                       'remote': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000001", 'size': 3, 'gdoc': False}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)
        org['file9']['changed'] = 'time'
        org['file9']['which'] = 1

        self.assertEqual(f, org)
        self.assertEqual(cf, {'file9' : {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.remote}})

    def test_calc_diffs_changed_R_time(self):
        """
        This tests if a file is marked as changed correctly (Remote Changed)
        Results: f[name]['changed'] == 'time'
        """
        f = {'file10': {'local': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 3},
                       'previous': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 3, 'rtime': "2017-12-20 15:43:27.776000001"},
                       'remote': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000002", 'size': 3, 'gdoc': False}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)
        org['file10']['changed'] = 'time'
        org['file10']['which'] = 2

        self.assertEqual(f, org)
        self.assertEqual(cf, {'file10' : {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.local}})

    def test_calc_diffs_changed_B_time(self):
        """
        This tests if a file is marked as changed correctly (Both Changed)
        Results: f[name]['changed'] == 'time'
        """
        f = {'file11': {'local': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000003", 'size': 3},
                       'previous': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 3, 'rtime': "2017-12-20 15:43:27.776000001"},
                       'remote': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000002", 'size': 3, 'gdoc': False}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)
        org['file11']['changed'] = 'time'
        org['file11']['which'] = 3

        self.assertEqual(f, org)
        self.assertEqual(cf, {'file11' : {'action' : RClone.Action.conflict, 'direction' : RClone.Direction.neither}})

    def test_calc_diffs_changed_R_size(self):
        """
        This tests if a file is marked as changed correctly (Remote Changed)
        Results: f[name]['changed'] == 'size'
        """
        f = {'file12': {'local': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 3},
                       'previous': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 3},
                       'remote': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 4, 'gdoc': False}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)

        org['file12']['changed'] = 'size'
        org['file12']['which'] = 2
        self.assertEqual(f, org)
        self.assertEqual(cf, {'file12' : {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.local}})

    def test_calc_diffs_changed_L_size(self):
        """
        This tests if a file is marked as changed correctly (Local Changed)
        Results: f[name]['changed'] == 'size'
        """
        f = {'file13': {'local': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 4},
                       'previous': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 3},
                       'remote': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 3, 'gdoc': False}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)

        org['file13']['changed'] = 'size'
        org['file13']['which'] = 1
        self.assertEqual(f, org)
        self.assertEqual(cf, {'file13' : {'action' : RClone.Action.copyto, 'direction' : RClone.Direction.remote}})

    def test_calc_diffs_changed_B_size(self):
        """
        This tests if a file is marked as changed correctly (Both Changed)
        Results: f[name]['changed'] == 'size'
        """
        f = {'file14': {'local': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 4},
                       'previous': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 3},
                       'remote': {'md5sum': "1", 'time': "2017-12-20 15:43:27.776000000", 'size': 5, 'gdoc': False}}}
        org = copy.deepcopy(f)

        cf = calc_diffs(f)

        org['file14']['changed'] = 'size'
        org['file14']['which'] = 3
        self.assertEqual(f, org)
        self.assertEqual(cf, {'file14' : {'action' : RClone.Action.conflict, 'direction' : RClone.Direction.neither}})

if(__name__ == '__main__'):
    unittest.main()
