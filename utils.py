import json
import os 
import tarfile

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


def remove_processed_from_id_list(id_list, processed_log, failed_log):
    """ Remove already processed documents and documents that could not be processed
        from list

    Args:
        id_list (list): List of document IDs
        processed_log (string): Path to log containing IDs of processed documents
        failed_log (string): Path to log containing IDs of documents that could 
                             not be processed

    Returns:
        list: List of document IDs whose PDF and abstract have not been processed yet
    """
    if os.path.isfile(failed_log):
        with open(failed_log, "r") as f:
            failed_to_process = f.read().splitlines()
    else:
        failed_to_process = []

    if os.path.isfile(processed_log):
        with open(processed_log, "r") as f:
            processed = f.read().splitlines()
    else:
        processed = []

    id_list = [
        doc_id for doc_id in id_list if (
            doc_id not in failed_to_process and doc_id not in processed
        )
    ] # remove ids whose articles could not be processed or whose have already been processed
    return id_list

# def remove_processed_from_id_list(fname_list, converted_log):
#     """ Removes from list documents that have already been converted 

#     Args:
#         fname_list (list): list of PDF names 
#         converted_log (string): path to log containing IDs of converted documents
#     Returns:
#         list: list of document IDs whose PDF has not been converted yet
#     """
#     if os.path.isfile(converted_log):
#         with open(converted_log, "r") as f:
#             converted = f.read().splitlines()
#     else:
#         converted = []

#     fname_list = [doc_id for doc_id in fname_list if os.path.splitext(doc_id)[0] not in converted] 
#     return fname_list

def compress_dir(tar_path, output_folder):
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(
            output_folder, 
            arcname=os.path.basename(output_folder)
        ) 