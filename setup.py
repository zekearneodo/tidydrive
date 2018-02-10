from setuptools import setup

setup(name='tidydrive',
      version='0.1',
      description='hi level functions to browse and download/upload drives from google drive',
      url='http://github.com/zekearneodo/tidydrive',
      author='Zeke Arneodo',
      author_email='earneodo@ucsd.edu',
      license='MIT',
      packages=['tidydrive'],
      requires=['os', 'apiclient.http', 'googleapiclient', 'hashlib', 'tqdm'],
      dependency_links=['tqdm'],
      zip_safe=False)