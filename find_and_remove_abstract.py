import argparse 
import os 
import shutil 
from tqdm import tqdm 

from PIL import Image, ImageDraw

def find_abstract(page_path):
    doc_lines = []
    span = []
    remaining = "introduction"

    with open(page_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.rstrip().split("\t")
            word_text = line[0]

            if len(remaining) > 0:
                if remaining.startswith(word_text.lower()):
                    remaining = remaining[len(word_text):].strip()
                    span.append(i)
                else:
                    remaining = "introduction"
                    span = []

            doc_lines.append(line)

    if not remaining: 
        with open(page_path, "w", encoding="utf-8") as fw:
            for i in range(span[0], len(doc_lines)):
                fw.write("\t".join(doc_lines[i]) + "\n")

        return (doc_lines, span) 
    else:
        return None


def update_doc(page_path, image_path, output_image_path):
    res = find_abstract(page_path)

    if res:
        doc_lines, span = res
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        img_width, img_height = image.size
        width, height = doc_lines[0][5:7]
        width, height = int(width), int(height)
        scale_w = img_width / width
        scale_h = img_height / height

        for i, line in enumerate(doc_lines):
            if i < span[0]:
                box = line[1:5]
                box = [int(b) for b in box]
                scaled_box = [box[0] * scale_w, box[1] * scale_h, box[2] * scale_w, box[3] * scale_h]

                draw.rectangle(scaled_box, fill="black")

        image.save(output_image_path)
        return True
    else:
        return False


def main(args):
    doc_dirs = sorted(os.listdir(args.text_dir))

    for doc_id in tqdm(doc_dirs):
        doc_path = os.path.join(
            os.path.join(args.text_dir, doc_id),
            f"{doc_id}_1.txt"
        )

        image_path = os.path.join(
            os.path.join(args.img_dir, doc_id), 
            doc_id + "_1.jpg"
        )

        output_image_path = os.path.join(
            os.path.join(args.output_img_dir, doc_id),
            f"{doc_id}_1.jpg"
        )

        if not update_doc(doc_path, image_path, output_image_path):
            print(f"Failed to find abstract in {doc_id}")
        



if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--text_dir",
        default=None,
        type=str,
        required=True,
        help="The input data dir. Should contain the txt files.",
    )
    parser.add_argument(
        "--img_dir",
        default=None,
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_img_dir",
        default=None,
        type=str,
        required=True,
    )
    parser.add_argument(
        "--dataset_name",
        default=None,
        stype=str,
        required=True,
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory."
    )

    args = parser.parse_args()

    if args.output_img_dir == args.img_dir:
        print(f"Overwriting first document pages in {args.img_dir}")
    else:
        if os.listdir(args.output_img_dir):
            if args.overwrite_output_dir:
                print(f"Overwriting {args.output_img_dir}")
                shutil.rmtree(args.output_img_dir)
                os.makedirs(args.output_img_dir)
            else:
                raise ValueError(
                    f"Output directory ({args.output_img_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )

    main(args)