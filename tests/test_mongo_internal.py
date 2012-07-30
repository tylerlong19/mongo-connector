"""Tests methods from mongo_internal
"""

import os
import sys
import inspect
file = inspect.getfile(inspect.currentframe())
cmd_folder = os.path.realpath(os.path.abspath(os.path.split(file)[0]))
cmd_folder = cmd_folder.rsplit("/", 1)[0]
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)

import unittest
import time
import json
from mongo_internal import Connector
from optparse import OptionParser
from setup_cluster import start_cluster
from bson.timestamp import Timestamp
from util import long_to_bson_ts

main_address = '27217'


class MongoInternalTester(unittest.TestCase):

    def runTest(self):
        unittest.TestCase.__init__(self)

    def test_connector(self):
        """Test whether the connector initiates properly
        """

        c = Connector(main_address, 'config.txt', None, ['test.test'],
                      '_id', None)
        c.start()

        while len(c.shard_set) != 1:
            time.sleep(2)
        c.join()

        self.assertFalse(c.can_run)
        time.sleep(5)
        for thread in c.shard_set.values():
            self.assertFalse(thread.running)

    def test_write_oplog_progress(self):
        """Test write_oplog_progress under several circumstances
        """
        os.system('touch temp_config.txt')
        config_file_path = os.getcwd() + '/temp_config.txt'
        c = Connector(main_address, config_file_path, None, ['test.test'],
                      '_id', None)

        #test that None is returned if there is no config file specified.
        self.assertEqual(c.write_oplog_progress(), None)

        c.oplog_progress_dict[1] = Timestamp(12, 34)
        #pretend to insert a thread/timestamp pair
        c.write_oplog_progress()

        data = json.load(open(config_file_path, 'r'))
        self.assertEqual(1, int(data[0]))
        self.assertEqual(long_to_bson_ts(int(data[1])), Timestamp(12, 34))

        #ensure the temp file was deleted
        self.assertFalse(os.path.exists(config_file_path + '~'))

        #ensure that updates work properly
        c.oplog_progress_dict[1] = Timestamp(44, 22)
        c.write_oplog_progress()

        data = json.load(open(config_file_path, 'r'))
        self.assertEqual(1, int(data[0]))
        self.assertEqual(long_to_bson_ts(int(data[1])), Timestamp(44, 22))

        os.system('rm ' + config_file_path)
        print 'PASSED TEST WRITE OPLOG PROGRESS'

    def test_read_oplog_progress(self):
        """Test read_oplog_progress
        """

        c = Connector(main_address, None, None, ['test.test'], '_id',
                      None)

        #testing with no file
        self.assertEqual(c.read_oplog_progress(), None)

        os.system('touch temp_config.txt')
        config_file_path = os.getcwd() + '/temp_config.txt'
        c.oplog_checkpoint = config_file_path

        #testing with empty file
        self.assertEqual(c.read_oplog_progress(), None)

        #add a value to the file, delete the dict, and then read in the value
        c.oplog_progress_dict['oplog1'] = Timestamp(12, 34)
        c.write_oplog_progress()
        del c.oplog_progress_dict['oplog1']

        self.assertEqual(len(c.oplog_progress_dict), 0)

        c.read_oplog_progress()

        self.assertTrue('oplog1' in c.oplog_progress_dict.keys())
        self.assertTrue(c.oplog_progress_dict['oplog1'], Timestamp(12, 34))

        c.oplog_progress_dict['oplog1'] = Timestamp(55, 11)

        #see if oplog progress dict is properly updated
        c.read_oplog_progress()
        self.assertTrue(c.oplog_progress_dict['oplog1'], Timestamp(55, 11))

        os.system('rm ' + config_file_path)
        print 'PASSED TEST READ OPLOG PROGRESS'

if __name__ == '__main__':
    os.system('rm config.txt; touch config.txt')

    parser = OptionParser()

    #-m is for the main address, which is a host:port pair, ideally of the
    #mongos. For non sharded clusters, it can be the primary.
    parser.add_option("-m", "--main", action="store", type="string",
                      dest="main_addr", default="27217")

    (options, args) = parser.parse_args()
    main_address = "localhost:" + options.main_addr
    if options.main_addr != "27217":
        start_cluster(use_mongos=False)
    else:
        start_cluster(use_mongos=True)

    unittest.main(argv=[sys.argv[0]])