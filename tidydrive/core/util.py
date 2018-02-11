import os
import hashlib


def md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def path_parts(path):
  path_parts = []
  while(True):
    path, folder = os.path.split(os.path.abspath(path))
    if (folder == ''):
      break
    path_parts.append(folder)
  return path_parts[::-1]
