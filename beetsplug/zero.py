# -*- coding: utf-8 -*-
# This file is part of beets.
# Copyright 2016, Blemjhoo Tezoulbr <baobab@heresiarch.info>.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

""" Clears tag fields in media files."""

from __future__ import division, absolute_import, print_function

import re
from beets.plugins import BeetsPlugin
from beets.mediafile import MediaFile
from beets.importer import action
from beets.util import confit

__author__ = 'baobab@heresiarch.info'
__version__ = '0.10'


class ZeroPlugin(BeetsPlugin):
    def __init__(self):
        super(ZeroPlugin, self).__init__()

        self._register_listeners()
        self._set_default_configuration()

        self.warned = False

        if self._has_contradictory_configuration():
            self._log.warn(u'cannot blacklist and whitelist at the same time')

        if self.config['fields']:
            self._strategy = ZeroBlacklist(self.config, self._log)
        elif self.config['keep_fields']:
            self._strategy = ZeroWhitelist(self.config, self._log)

    def _register_listeners(self):
        self.register_listener('write', self.write_event)
        self.register_listener('import_task_choice',
                               self.import_task_choice_event)

    def _set_default_configuration(self):
        self.config.add({
            'fields': [],
            'keep_fields': [],
            'update_database': False,
        })

    def _has_contradictory_configuration(self):
        return self.config['fields'] and self.config['keep_fields']

    def import_task_choice_event(self, session, task):
        """Listen for import_task_choice event."""
        if task.choice_flag == action.ASIS and not self.warned:
            self._log.warn(u'cannot zero in \"as-is\" mode')
            self.warned = True
        # TODO request write in as-is mode

    def write_event(self, item, path, tags):
        self._strategy.handle_item(item, tags)


class ZeroBlacklist(object):
    def __init__(self, configuration, logger):
        self._log = logger
        self.patterns = {}
        self._configuration = configuration
        self._validate_configuration()

        for field in self._configuration['fields'].as_str_seq():
            self.set_pattern(field)

    def _validate_configuration(self):
        for field in self._configuration['fields'].as_str_seq():
            if field not in MediaFile.fields():
                self._log.error(u'invalid field: {0}', field)
                continue
            if field in ('id', 'path', 'album_id'):
                self._log.warn(u'field \'{0}\' ignored, zeroing '
                               u'it would be dangerous', field)
                continue

    def set_pattern(self, field):
        try:
            self.patterns[field] = self._configuration[field].as_str_seq()
        except confit.NotFoundError:
            # Matches everything
            self.patterns[field] = True

    def match_patterns(self, field, patterns):
        if patterns is True:
            return True
        for p in patterns:
            if re.search(p, unicode(field), flags=re.IGNORECASE):
                return True
        return False

    def handle_item(self, item, tags):
        """Set values in tags to `None` if the key and value are matched
        by `self.patterns`.
        """
        if not self.patterns:
            self._log.warn(u'no fields, nothing to do')
            return

        for field, patterns in self.patterns.items():
            if field in tags:
                value = tags[field]
                match = self.match_patterns(tags[field], patterns)
            else:
                value = ''
                match = patterns is True

            if match:
                self._log.debug(u'{0}: {1} -> None', field, value)
                tags[field] = None
                if self._configuration['update_database']:
                    item[field] = None


class ZeroWhitelist(object):
    def __init__(self, configuration, logger):
        self._log = logger
        self.patterns = {}
        self._configuration = configuration
        self._validate_configuration()

        for field in MediaFile.fields():
            if field in self._configuration['keep_fields'].as_str_seq():
                continue
            self.set_pattern(field)

        # These fields should always be preserved.
        for key in ('id', 'path', 'album_id'):
            if key in self.patterns:
                del self.patterns[key]


    def _validate_configuration(self):
        for field in self._configuration['keep_fields'].as_str_seq():
            if field not in MediaFile.fields():
                self._log.error(u'invalid field: {0}', field)
                continue

    def set_pattern(self, field):
        try:
            self.patterns[field] = self._configuration[field].as_str_seq()
        except confit.NotFoundError:
            # Matches everything
            self.patterns[field] = True

    def match_patterns(self, field, patterns):
        if patterns is True:
            return True
        for p in patterns:
            if re.search(p, unicode(field), flags=re.IGNORECASE):
                return True
        return False

    def handle_item(self, item, tags):
        """Set values in tags to `None` if the key and value are matched
        by `self.patterns`.
        """
        if not self.patterns:
            self._log.warn(u'no fields, nothing to do')
            return

        for field, patterns in self.patterns.items():
            if field in tags:
                value = tags[field]
                match = self.match_patterns(tags[field], patterns)
            else:
                value = ''
                match = patterns is True

            if match:
                self._log.debug(u'{0}: {1} -> None', field, value)
                tags[field] = None
                if self._configuration['update_database']:
                    item[field] = None
