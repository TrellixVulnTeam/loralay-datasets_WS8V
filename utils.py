import json

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
