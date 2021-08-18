import json
import os 

def get_ids(input_file, limit):
    id_list = []
    num_processed = 0
    with open(input_file, "r") as f:
        for line in f:
            item = json.loads(line)
            id_list.append(item["article_id"])
            num_processed += 1
            if num_processed == limit:
                break
    
    return id_list


def remove_downloaded_from_id_list(id_list, downloaded_log, failed_log):
    """ Remove already downloaded documents and documents that could not be downloaded
        from list

    Args:
        id_list (list): List of document IDs
        downloaded_log (string): Path to log containing IDs of downloaded documents
        failed_log (string): Path to log containing IDs of documents that could 
                             not be downloaded

    Returns:
        list: List of document IDs whose PDF and abstract have not been downloaded yet
    """
    if os.path.isfile(failed_log):
        with open(failed_log, "r") as f:
            failed_to_download = f.read().splitlines()
    else:
        failed_to_download = []

    if os.path.isfile(downloaded_log):
        with open(downloaded_log, "r") as f:
            downloaded = f.read().splitlines()
    else:
        downloaded = []

    id_list = [
        doc_id for doc_id in id_list if (
            doc_id not in failed_to_download and doc_id not in downloaded
        )
    ] # remove ids whose articles could not be downloaded or whose have already been downloaded
    return id_list

def remove_converted_from_id_list(fname_list, converted_log):
    """ Removes from list documents that have already been converted 

    Args:
        fname_list (list): list of PDF names 
        converted_log (string): path to log containing IDs of converted documents
    Returns:
        list: list of document IDs whose PDF has not been converted yet
    """
    if os.path.isfile(converted_log):
        with open(converted_log, "r") as f:
            converted = f.read().splitlines()
    else:
        converted = []

    fname_list = [doc_id for doc_id in fname_list if os.path.splitext(doc_id)[0] not in converted] 
    return fname_list