# vim: tabstop=4 shiftwidth=4 softtabstop=4

import os
import tempfile
import unittest2

from migrate.versioning import api as migrate_api
from migrate.versioning import repository as repo
from migrate.exceptions import DatabaseNotControlledError

from opencenter.db import migrate_repo as opencenter_repo
from opencenter.db.database import init_db


class SqlMigrationTests(unittest2.TestCase):
    def _initialize_sql(self, uri):
        init_db(uri, migrate=False)

    def setUp(self):
        (_, self.tmp_file) = tempfile.mkstemp()
        self.uri = 'sqlite:///%s' % self.tmp_file
        self.repo_path = self._find_repo()
        self._initialize_sql(self.uri)
        pass

    def tearDown(self):
        os.remove(self.tmp_file)

    def test_full_upgrade_and_downgrade(self):
        self._upgrade_db()
        self._downgrade_db()

    def _upgrade_db(self, version=None):
        if version is None:
            version = migrate_api.version(str(self.repo_path))

        try:
            db_ver = migrate_api.db_version(self.uri, self.repo_path)
        except DatabaseNotControlledError:
            migrate_api.version_control(self.uri, self.repo_path)
            db_ver = migrate_api.db_version(self.uri, self.repo_path)

        migrate_api.upgrade(self.uri, self.repo_path, version)

    def _downgrade_db(self, version=None):
        if version is None:
            version = 0
        migrate_api.downgrade(self.uri, self.repo_path, version)

    def _find_repo(self):
        return repo.Repository(
            os.path.abspath(os.path.dirname(opencenter_repo.__file__)))
