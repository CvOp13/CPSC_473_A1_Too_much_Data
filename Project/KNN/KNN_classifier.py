import os
import sys

import numpy as np
from PIL import Image

def get_arguments():
    """
    Gets the needed arguments from the command line and prints 
    a usage message if they are malformed.

    Returns:
        The path to the dataset
    """
    try:
        dataset_path = sys.argv[1]
    except IndexError:
        print("Usage: KNN_classifier.py <training data directory>")
        print("Example: KNN_classifier.py dataset")
        sys.exit(1)
    return dataset_path 

def load_data(path):
    """
    Loads the image data from the directory specified by the provided path then returns it as two numpy arrays.

    Args:
        path: The provided path
    Returns:
        A tuple first containing the image data then the labels for said image data both as numpy arrays.
    """
    # List of numpy arrays representing images
    images = []
    # List of values to predict for each image.
    labels = []
    num_broken_files = 0
    WILDFIRE_LABEL = "wildfire"

    # Directory structure is dataset/<train test or valid>/<wildfire or no wildfire>/image_name

    def process_image_directory(sub_entry, sub_entry_path):
        for image_name in os.listdir(sub_entry_path):
            image_path = sub_entry_path + "/" + image_name 
            image = Image.open(image_path)
            try:
                image_array = np.asarray(image)
            except OSError:
                nonlocal num_broken_files
                num_broken_files += 1
                continue

            images.append(image_array)
            if sub_entry == WILDFIRE_LABEL:
                labels.append(1)            
            else:
                labels.append(0)            

    entries = os.listdir(path)
    for entry in entries:
        entry_path = path + "/" + entry
        for sub_entry in os.listdir(entry_path):
            sub_entry_path = entry_path + "/" + sub_entry
            process_image_directory(sub_entry, sub_entry_path)

    print(f"{num_broken_files} broken files in dataset.")
    array_images = np.array(images)
    array_labels = np.array(labels)
    return array_images, array_labels

def shuffle_data(images, labels, random_generator):
    """
    Shuffles the data used for training, testing and validation.

    Args:
        images: The images to use to train the model
        labels: The label for each image in images
        random_generator: The numpy Generator to use.
    Returns:
        A tuple first containing the shuffled image data then the labels for said image data both as numpy arrays.
    """
    length = len(images)
    shuffled_indexes = random_generator.permutation(length)
    shuffled_images = images[shuffled_indexes]
    shuffled_labels = labels[shuffled_indexes]

    return shuffled_images, shuffled_labels

def main():
    dataset_path = get_arguments()
    random_generator = np.random.default_rng()
    images, labels = load_data(dataset_path)
    print(images[[0, 3, 4]])
    print(labels[[0, 3, 4]])
    shuffled_images, shuffled_labels = shuffle_data(images, labels, random_generator)
    print(shuffled_images[[0, 3, 4]])
    print(shuffled_labels[[0, 3, 4]])


if __name__ == "__main__":
    main()
