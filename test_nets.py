from keras.layers import Conv2D, AveragePooling2D, Dense, BatchNormalization, LeakyReLU, GlobalAveragePooling2D, Dropout, Input
from keras.models import Model
from keras.models import model_from_json
from keras.regularizers import l2
import keras

import matplotlib
# matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.style.use('seaborn-bright')
import matplotlib.ticker as plticker

import time
import json
import pickle
from random import shuffle
import os
import numpy as np
import matplotlib.patches as patches

import PIL
from PIL import Image
from keras.preprocessing import image
from keras.preprocessing.image import ImageDataGenerator
from crop_generator import yield_crops

dataset_path = "dataset-ethz101food"

def ix_to_class_name(idx):
    with open(os.path.join(dataset_path, "meta", "classes.txt")) as file:
        class_labels = [line.strip('\n') for line in file.readlines()]
    return class_labels[idx]

def class_name_to_idx(name):
    with open(os.path.join(dataset_path, "meta", "classes.txt")) as file:
        class_labels = [line.strip('\n') for line in file.readlines()]
        for i, label_name in enumerate(class_labels):
            if label_name == name:
                return i
        else:
            print("class idx not found!")
            exit(-1)


def eval_on_orig_cropped_test_set(model, input_size, input_name, preprocess_func):
    test_datagen = ImageDataGenerator(preprocessing_function=preprocess_func)
    validation_generator = test_datagen.flow_from_directory(
        'dataset-ethz101food/test',
        target_size=input_size,
        batch_size=1,
        class_mode='categorical')
    model.compile(loss='categorical_crossentropy', optimizer='rmsprop', metrics=['categorical_accuracy'])
    (loss, acc) = model.evaluate_generator(validation_generator)
    print("Original classification accuracy: {:.4f}%".format(acc * 100))



    model.compile(loss='categorical_crossentropy', optimizer='rmsprop', metrics=['categorical_accuracy'])
    (loss, acc) = model.evaluate_generator(yield_crops(cropfilename="results/cropping_eval/cropsdata.pickle",
                                                          input_size=input_size,
                                                          preprocess_func=preprocess_func,
                                                          input_name=input_name), 25250)
    print("Crop classification accuracy: {:.4f}%".format(acc * 100))


# -----------------------------------
# CLFs
vgg16CLF = keras.applications.vgg16.VGG16(include_top=False, weights='imagenet', input_shape=(224, 224, 3))
x = GlobalAveragePooling2D()(vgg16CLF.output)
out = Dense(101, activation='softmax', name='output_layer')(x)
vgg16CLF = Model(inputs=vgg16CLF.input, outputs=out)
vgg16CLF.load_weights("trained_models/top5_vgg16_acc77_2017-12-24/vgg16_ft_weights_acc0.78_e15_2017-12-23_22-53-03.hdf5")

vgg19CLF = keras.applications.vgg19.VGG19(include_top=False, weights='imagenet', input_shape=(224, 224, 3))
x = GlobalAveragePooling2D()(vgg19CLF.output)
out = Dense(101, activation='softmax', name='output_layer')(x)
vgg19CLF = Model(inputs=vgg19CLF.input, outputs=out)
vgg19CLF.load_weights("trained_models/top4_vgg19_acc78_2017-12-23/vgg19_ft_weights_acc0.78_e26_2017-12-22_23-55-53.hdf5")

xceptionCLF = keras.applications.xception.Xception(include_top=False, weights='imagenet', input_shape=(299, 299, 3))
x = GlobalAveragePooling2D()(xceptionCLF.output)
out = Dense(101, activation='softmax', name='output_layer')(x)
xceptionCLF = Model(inputs=xceptionCLF.input, outputs=out)
xceptionCLF.load_weights("trained_models/top1_xception_acc80_2017-12-25/xception_ft_weights_acc0.81_e9_2017-12-24_13-00-22.hdf5")

incresv2CLF = keras.applications.inception_resnet_v2.InceptionResNetV2(include_top=False, weights='imagenet', input_shape=(299, 299, 3))
x = GlobalAveragePooling2D()(incresv2CLF.output)
out = Dense(101, activation='softmax', name='output_layer')(x)
incresv2CLF = Model(inputs=incresv2CLF.input, outputs=out)
incresv2CLF.load_weights("trained_models/top2_incresnetv2_acc79_2017-12-22/incv2resnet_ft_weights_acc0.79_e4_2017-12-21_09-02-16.hdf5")

incv3CLF = keras.applications.inception_v3.InceptionV3(include_top=False, weights='imagenet', input_shape=(299, 299, 3))
x = GlobalAveragePooling2D()(incv3CLF.output)
x = Dense(1024, kernel_initializer='he_uniform', bias_initializer="he_uniform", kernel_regularizer=l2(.0005), bias_regularizer=l2(.0005))(x)
x = LeakyReLU()(x)
x = BatchNormalization()(x)
x = Dropout(0.5)(x)
x = Dense(512, kernel_initializer='he_uniform', bias_initializer="he_uniform", kernel_regularizer=l2(.0005), bias_regularizer=l2(.0005))(x)
x = LeakyReLU()(x)
x = BatchNormalization()(x)
x = Dropout(0.5)(x)
out = Dense(101, kernel_initializer='he_uniform', bias_initializer="he_uniform", activation='softmax', name='output_layer')(x)
incv3CLF = Model(inputs=incv3CLF.input, outputs=out)
incv3CLF.load_weights("trained_models/top3_inceptionv3_acc79_2017-12-27/inceptionv3_ft_weights_acc0.79_e10_2017-12-25_22-10-02.hdf5")


print("VGG16")
eval_on_orig_cropped_test_set(vgg16CLF, (224, 224), "input_1", keras.applications.vgg16.preprocess_input)

print("\nVGG19")
eval_on_orig_cropped_test_set(vgg19CLF, (224, 224), "input_2", keras.applications.vgg19.preprocess_input)

print("\nXCEPTION")
eval_on_orig_cropped_test_set(xceptionCLF, (299, 299), "input_3", keras.applications.xception.preprocess_input)

print("\nINCEPTION_RESNET_V2")
eval_on_orig_cropped_test_set(incresv2CLF, (299, 299), "input_4", keras.applications.inception_resnet_v2.preprocess_input)

print("\nINCEPTION_V3")
eval_on_orig_cropped_test_set(incv3CLF, (299, 299), "input_5", keras.applications.inception_v3.preprocess_input)
