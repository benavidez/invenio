# -*- coding: utf-8 -*-
##
## This file is part of Invenio.
## Copyright (C) 2011 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

'''
WebAuthorProfile Database interface
'''

from invenio.dbquery import run_sql
from invenio.config import CFG_WEBAUTHORPROFILE_CACHE_EXPIRED_DELAY_BIBSCHED

def _create_db_tables():
    '''
    Temporary method to create/reset cache tables.
    sql code will be moved to the official sql install file.
    '''
    run_sql("""CREATE TABLE IF NOT EXISTS `wapCACHE` (
          `object_name` varchar(120) NOT NULL,
          `object_key` varchar(120) NOT NULL,
          `object_value` longtext,
          `object_status` varchar(120),
          `last_updated` datetime NOT NULL,
          PRIMARY KEY  (`object_name`,`object_key`),
          INDEX `name-b` (`object_name`),
          INDEX `key-b` (`object_key`),
          INDEX `last_updated-b` (`last_updated`)
        ) ENGINE=MyISAM;
        """)

def get_cached_element(name, key):
    '''
    Returns a cached element as [element_value, last_updated, is_up_to_date, is_present_in_cache]
    '''
    el = run_sql("select object_value, object_status, last_updated from wapCACHE "
             "where object_name=%s and object_key=%s",
             (str(name), str(key)))
    if len(el) == 0:
        return {'value':'', 'upToDate':False, 'last_updated':None, 'present':False}
    else:
        status = True
        precached = False
        if el[0][1] != 'UpToDate':
            status = False
        if el[0][1] == 'Precached':
            precached = True

        return {'value':el[0][0], 'upToDate':status, 'last_updated':el[0][2], 'present':True, 'precached':precached}

def precache_element(name, key):
    '''
    Updates the last_updated flag of a cache to prevent parallel recomputation of the same cache.
    '''
    run_sql("insert into wapCACHE  (object_name,object_key,last_updated) values (%s,%s,now()) "
            "on duplicate key update last_updated=now(),object_status=%s",
            (str(name), str(key), 'Precached'))

def cache_element(name, key, value):
    '''
    Insert an element into cache or update already present element
    '''
    present = run_sql("select object_name,object_key from wapCACHE where "
                      "object_name=%s and object_key=%s", (str(name), str(key)))

    if len(present) > 0:
        run_sql("update wapCACHE set object_value=%s,object_status=%s,"
                "last_updated=now() where object_name=%s and object_key=%s",
                (str(value), 'UpToDate', str(name), str(key)))
    else:
        run_sql("insert into wapCACHE values (%s,%s,%s,%s,now())",
                (str(name), str(key), str(value), 'UpToDate'))


def expire_cache_element(name, key):
    '''
    Sets cache element status to 'Expired' 
    '''
    run_sql("update wapCACHE set object_status=%s where "
            "object_name=%s and object_key=%s", ('Expired', str(name), str(key)))

def expire_all_cache_for_person(person_id):
    '''
    expires al caches for person n.canonical.1
    '''
    run_sql("update wapCACHE set object_status=%s where "
            "object_key=%s", ('Expired', 'pid:' + str(person_id)))

def get_expired_person_ids(expire_delay_days=CFG_WEBAUTHORPROFILE_CACHE_EXPIRED_DELAY_BIBSCHED):
    '''
    pids with expired caches
    '''
    keys = run_sql("select object_key from wapCACHE where object_status=%s or last_updated < "
                   "timestampadd(day, -%s, now())", ('Expired',expire_delay_days))
    keys = [x[0].split(':')[1] for x in set(keys) if ':' in x[0]]
    return keys