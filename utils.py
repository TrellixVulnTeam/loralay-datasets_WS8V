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

def get_abstracts(input_file, limit):
    abstract_list = []
    num_processed = 0
    with open(input_file, "r") as f:
        for line in f:
            item = json.loads(line)
            abstract_text = item["abstract_text"]
            abstract_text = abstract_text.replace("<S>", "").replace("</S>", "")
            abstract_list.append(abstract_text)
            num_processed += 1
            if num_processed == limit:
                break

    return abstract_list
