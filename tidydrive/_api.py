import json
import logging
import io
import sys
import os
import time
import tqdm

from apiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient import errors

logger = logging.getLogger('tidydrive.api')


def get_file_item(service, file_id, retries=5):
    for n in range(retries):
        try:
            file_item = service.files().get(fileId=file_id, fields='id, name, size').execute()
            return file_item
        except errors.HttpError as e:
            error = json.loads(e.content)
            if error.get('code') == 403 or error.get('code') == 503:
                logger.warning('Error  {}'.format(error.get('errors')[0].get('reason')))
                time.sleep((2 ** n))
            else:
                raise
    logger.warning('Error in get_file_item')
    return None


def download_chunk(downloader, retries=5):
    for n in range(retries):
        try:
            status, done = downloader.next_chunk()
            return status, done
        except errors.HttpError as e:
            error = json.loads(e.content)
            if error.get('code') == 403 or error.get('code') == 503 or error.get('code') == 500:
                logger.warning('Error  {}'.format(error.get('errors')[0].get('reason')))
                time.sleep((2 ** n))
            else:
                raise


def download_file(service, file_id, dest_path, retries=5, chunk_size=1048576):
    file_obj = get_file_item(service, file_id)
    file_name = file_obj['name']
    print(file_obj)
    logger.info('Downloading file {} to folder {}'.format(file_name, dest_path))
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(os.path.join(dest_path, file_name), 'wb')
    downloader = MediaIoBaseDownload(fh, request, chunksize=chunk_size)
    done = False
    total_chunks = int(file_obj['size']) // chunk_size
    sys.stdout.flush()
    progress_bar = tqdm.tqdm(total=total_chunks, unit='Mb',
                             desc='Dowloading file {}'.format(file_name))
    while done is False:
        try:
            status, done = download_chunk(downloader, retries=retries);
            progress_bar.update(1);
        except errors.HttpError as err:
            print(err)
            if int(err.resp['status']) == 503:
                logger.warning('Sevice Unavailable, retrying')
            else:
                raise

    logger.info('Download complete')
    return True


def upload_file(service, parent_obj, file_path, retries=5, chunk_size=1048576):
    file_size = os.path.getsize(file_path)

    file_metadata = {'name': os.path.split(file_path)[-1],
                     'parents': [parent_obj['id']],
                     'content-length': chunk_size,
                     'content-range': '*/{}'.format(file_size)}

    media = MediaFileUpload(file_path,
                            resumable=True,
                            chunksize=chunk_size)

    request = service.files().create(body=file_metadata,
                                               media_body=media)
    done = False
    total_chunks = int(file_size) // chunk_size
    logger.debug('file size {}'.format(file_size))

    bytes_in = 0
    response = None

    sys.stdout.flush()
    progress_bar = tqdm.tqdm(total=total_chunks, unit='Mb',
                             desc='Uploading file {}'.format(file_path))
    while response is None:
        try:
            # print('bytes in {}'.format(bytes_in))
            file_metadata['content_range'] = '{0}-{1}/{2}'.format(bytes_in,
                                                                  bytes_in + chunk_size,
                                                                  file_size)
            file_metadata['content-length'] = '{0}'.format(chunk_size)
            status, response = request.next_chunk()
            bytes_in = bytes_in + chunk_size
            chunk_size = min(chunk_size, file_size - bytes_in)
            progress_bar.update(1)

        except:
            err = sys.exc_info()[0]
            raise RuntimeWarning('An error occured while uploading {}'.format(err))
            logger.warning('aborted')
            return request, status, response

    tqdm.tqdm.write("Upload Complete!")
    return request, status, response
