from __future__ import absolute_import
import logging
import os

from ._util import path_parts
import ._api

from functools import wraps

logger = logging.getLogger('tidydrive')

def make_query(query_par):
    q = ""
    if query_par['parents']:
        q += "'{}' in parents".format(query_par['parents'])
    del query_par['parents']

    if query_par['trashed']:
        q += " and trashed={}".format(query_par['trashed'])
    del query_par['trashed']

    q_terms = ([" and {0}='{1}'".format(k, v) for k, v in query_par.items() if v])
    return {'q': ''.join([q] + q_terms)}

def path_wrapper(method):
    # wraps a function to accept either a file_obj dictionary or a path within the drive
    @wraps(method)
    def right_input_fun(obj, *args, **kwargs):
        if isinstance(args[0], str):
            # print('Entered string')
            file_obj = obj.get_by_path(args[0])
            # print('got file_obj {}'.format(file_obj))
        else:
            file_obj = args[0]
        return method(obj, file_obj, *args[1:], **kwargs)

    return right_input_fun


def unique_wrapper(method):
    @wraps(method)
    def check_and_call(tidy_drive, parent_file_obj, name, *args, **kwargs):
        if len(tidy_drive.get_single_child(name, parent_id=parent_file_obj['id'])) > 0:
            raise RuntimeError('File already exists {}'.format(name))
        return method(tidy_drive, parent_file_obj, name, *args, **kwargs)

    return check_and_call


def name_from_path(method):
    @wraps(method)
    def split_and_call(tidy_drive, parent_file_obj, local_path, *args, **kwargs):
        path, name = os.path.split(local_path)
        print('Spliting path into n: {}, path: {}'.format(name, path))
        return method(tidy_drive, parent_file_obj, name, path, *args, **kwargs)

    return split_and_call


class TidyDrive:
    def __init__(self, service):
        self.service = service
        self.query_fields = "files(id, name, mimeType, parents, size)"
        self.default_query_par = {'parents': None,
                                  'trashed': 'false',
                                  'title': None,
                                  'type': None,
                                  'pattern': None,
                                  'id': None
                                  }

    def get_single_child(self, name, parent_id='root'):
        query = "parents='{0}' and trashed=false and name='{1}'".format(parent_id, name)
        results = self.service.files().list(q=query,
                                            fields=self.query_fields).execute()
        list_found = items = results.get('files', [])
        if len(list_found) > 1:
            raise RuntimeError('Found more than 1 file with the name')
        return list_found

    def get_by_path(self, path, parent_id='root'):
        # gets a path relative to a parent_id
        # returns a query result
        path_list = path_parts(os.path.abspath(path))

        for name in path_list:
            # print(parent_id)
            found_in_parent = self.get_single_child(name, parent_id)
            # check that the size of found is exactly 1
            parent_id = found_in_parent[0]['id']

        # print(found_in_parent[0]['id'])
        return found_in_parent[0]

    @path_wrapper
    def isdir(self, file_obj):
        print('*isdir entered {}'.format(file_obj))
        return file_obj['mimeType'] == 'application/vnd.google-apps.folder'

    @path_wrapper
    def size(self, file_obj):
        raise NotImplementedError
        return file_obj['fileSize']

    @path_wrapper
    def listdir(self, file_obj):
        if not (self.isdir(file_obj) or file_obj['id'] == 'root'):
            raise ValueError('Not a dir {}'.format(file_obj))
        query = "parents='{0}' and trashed=false".format(file_obj['id'])
        results = self.service.files().list(q=query,
                                            fields=self.query_fields).execute()
        list_found = items = results.get('files', [])
        # return list_found
        return list(map(lambda x: x['name'], list_found))

    @path_wrapper
    def download_file(self, file_obj, dest_path):
        return api.download_file(self.service, file_obj['id'], dest_path, retries=5)

    @name_from_path
    @path_wrapper
    @unique_wrapper
    def upload_file(self, parent_obj, name, local_file_path):
        logger.debug('Upload file entered p_obj {} name {} local_path {}'.format(parent_obj,
                                                                                 name,
                                                                                 local_file_path))
        return api.upload_file(self.service, parent_obj, os.path.join(local_file_path, name))

    @path_wrapper
    @unique_wrapper
    def mkdir(self, parent_file_obj, name):
        if not (self.isdir(parent_file_obj) or parent_file_obj['id'] == 'root'):
            raise ValueError('Not a dir {}'.format(parent_file_obj))
        fold_meta = {'name': name,
                     'parents': [parent_file_obj['id']],
                     'mimeType': 'application/vnd.google-apps.folder'
                     }
        new_file = self.service.files().create(body=fold_meta, fields='id').execute()
        return new_file

    def move(self, source_file_obj, dest_file_obj):
        if not (self.isdir(dest_file_obj) or dest_file_obj['id'] == 'root'):
            raise ValueError('Not a dir {}'.format(dest_file_obj))
        file = self.service.files().get(fileId=source_file_obj['id'],
                                        fields='parents').execute();
        previous_parents = ",".join(file.get('parents'))
        file = self.service.files().update(fileId=source_file_obj['id'],
                                           addParents=dest_file_obj['id'],
                                           removeParents=previous_parents,
                                           fields='id, parents').execute()
        return file
