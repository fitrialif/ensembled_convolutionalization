from keras.layers import Conv2D, AveragePooling2D
from keras.models import Model
from keras.models import model_from_json
from PIL import Image

import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.style.use('seaborn-bright')
import matplotlib.ticker as plticker

import json
import os
import numpy as np

vgg16, vgg19, xception, *_ = range(10)
names = ["VGG16", "VGG19", "XCEPTION"]

MODELNAME = xception


if MODELNAME == vgg16:
    from keras.applications.vgg16 import preprocess_input
elif MODELNAME == vgg19:
    from keras.applications.vgg19 import preprocess_input
elif MODELNAME == xception:
    from keras.applications.xception import preprocess_input
else:
    print("Incorrect model name")
    exit()

from keras.preprocessing import image

def prepare_str_file_architecture_syntax(filepath):
    model_str = str(json.load(open(filepath, "r")))
    model_str = model_str.replace("'", '"')
    model_str = model_str.replace("True", "true")
    model_str = model_str.replace("False", "false")
    model_str = model_str.replace("None", "null")
    return model_str


def load_model(architecture_path, weigths_path, debug=False):
    model = model_from_json(prepare_str_file_architecture_syntax(architecture_path))
    model.load_weights(weigths_path)
    if debug:
        print("IMPORTED MODEL")
        model.summary()

    p_dim = model.get_layer("global_average_pooling2d_1").input_shape
    out_dim = model.get_layer("output_layer").get_weights()[1].shape[0]
    W, b = model.get_layer("output_layer").get_weights()

    weights_shape = (1, 1, p_dim[3], out_dim)

    if debug:
        print("weights old shape", W.shape, "values", W)
        print("biases old shape", b.shape, "values", b)
        print("weights new shape", weights_shape)

    W = W.reshape(weights_shape)

    if(MODELNAME == vgg16 or MODELNAME == vgg19):
        last_layer = model.get_layer("block5_pool")
    elif MODELNAME == xception:
        last_layer = model.get_layer("block14_sepconv2_act")

    last_layer.outbound_nodes = []
    model.layers.pop()
    model.layers.pop()

    if debug:
        for i, l in enumerate(model.layers):
            print(i, ":", l.name)

    return model, last_layer, W, b

if MODELNAME == vgg16:
    architecturepath = "trained_models/top5_vgg16_acc77_2017-12-24/vgg16_architecture_2017-12-23_22-53-03.json"
    weightpath = "trained_models/top5_vgg16_acc77_2017-12-24/vgg16_ft_weights_acc0.78_e15_2017-12-23_22-53-03.hdf5"
    pool_size =(7, 7)
    trained_img_size = 224
elif MODELNAME == vgg19:
    architecturepath = "trained_models/top4_vgg19_acc78_2017-12-23/vgg19_architecture_2017-12-22_23-55-53.json"
    weightpath = "trained_models/top4_vgg19_acc78_2017-12-23/vgg19_ft_weights_acc0.78_e26_2017-12-22_23-55-53.hdf5"
    pool_size =(7, 7)
    trained_img_size = 224
elif MODELNAME == xception:
    architecturepath = "trained_models/top1_xception_acc80_2017-12-25/xception_architecture_2017-12-24_13-00-22.json"
    weightpath = "trained_models/top1_xception_acc80_2017-12-25/xception_ft_weights_acc0.81_e9_2017-12-24_13-00-22.hdf5"
    pool_size =(10, 10)
    trained_img_size = 308

base_1, last_layer, W, b = load_model(architecturepath, weightpath)
x = AveragePooling2D(pool_size=pool_size, strides=(1, 1))(last_layer.output)
x = Conv2D(101, (1, 1), strides=(1, 1), name='conv2d_civo', activation='softmax', padding='valid', weights=[W, b])(x)
overlap_fcn = Model(inputs=base_1.input, outputs=x)

base_2, last_layer, W, b = load_model(architecturepath, weightpath)
x = AveragePooling2D(pool_size=pool_size)(last_layer.output)
x = Conv2D(101, (1, 1), strides=(1, 1), name='conv2d_civo', activation='softmax', padding='valid', weights=[W, b])(x)
upsample_fcn = Model(inputs=base_2.input, outputs=x)

upsample_fcn.summary()

def idx_to_class_name(idx):
    with open(os.path.join('dataset-ethz101food', 'meta', 'classes.txt')) as file:
        class_labels = [line.strip('\n') for line in file.readlines()]
    return class_labels[idx]

def save_map(heatmap, resultfname, input_size, tick_interval=None, is_input_img=False):
    if is_input_img:
        image = Image.open(heatmap)
        image = image.resize(input_size, Image.ANTIALIAS)
        imgarray = np.asarray(image)
    else:
        pixels = 255 * (1.0 - heatmap)
        image = Image.fromarray(pixels.astype(np.uint8), mode='L')
        image = image.resize(input_size, Image.NEAREST)
        imgarray = np.asarray(image)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    if tick_interval:
        myInterval = tick_interval
        loc = plticker.MultipleLocator(base=myInterval)
        ax.xaxis.set_major_locator(loc)
        ax.yaxis.set_major_locator(loc)
        ax.grid(which='both', axis='both', linestyle='-')

    if is_input_img:
        ax.imshow(imgarray)
    else:
        ax.imshow(imgarray, cmap='Greys_r', interpolation='none')

    if tick_interval:
        nx = abs(int(float(ax.get_xlim()[1] - ax.get_xlim()[0]) / float(myInterval)))
        ny = abs(int(float(ax.get_ylim()[1] - ax.get_ylim()[0]) / float(myInterval)))
        for jj in range(ny):
            y = myInterval / 2 + jj * myInterval
            for ii in range(nx):
                x = myInterval / 2. + float(ii) * myInterval
                ax.text(x, y, '{:d}'.format((ii + jj * nx) + 1), color='tab:blue', ha='center', va='center')

    fig.savefig(resultfname)
    plt.close()

input_set = "test"
input_class = "cup_cakes"
input_instance = "2387290"
input_filename = "dataset-ethz101food/" + input_set + "/" + input_class + "/" + input_instance + ".jpg"

threshold_accuracy_stop = 0.80
max_upsampling_factor = 5
min_upsampling_factor = 1
top_n_show = 5

#model_modes = [overlap_fcn, upsample_fcn]
model_modes = [overlap_fcn]
for model in model_modes:
    if (os.path.exists(input_filename)):
        if model == overlap_fcn:
            input_image = image.load_img(input_filename)
            img_original_size = input_image.size
            input_image = image.img_to_array(input_image)
            input_image_expandedim = np.expand_dims(input_image, axis=0)
            input_preprocessed_image = preprocess_input(input_image_expandedim)

            preds = model.predict(input_preprocessed_image)
            print("input img shape (height, width)", input_image.shape, "preds shape", preds.shape)

            heatmaps_values = [preds[0, :, :, i] for i in range(101)]
            max_heatmaps = np.amax(heatmaps_values, axis=(1, 2))
            top_n_idx = np.argsort(max_heatmaps)[-top_n_show:][::-1]

            resultdir = os.path.join(os.getcwd(), "results", names[MODELNAME],input_class + "_" + input_instance + "_standard-heatmaps")
            if (os.path.isdir(resultdir)):
                print("Deleting older version of the folder " + resultdir)
                shutil.rmtree(resultdir)
            os.makedirs(resultdir)

            save_map(input_filename, os.path.join(resultdir, input_class + "_" + input_instance + ".jpg"), img_original_size, is_input_img=True)
            for i, idx in enumerate(top_n_idx):
                name_class = idx_to_class_name(idx)
                print("Top", i, "category is: id", idx, ", name", name_class)
                resultfname = os.path.join(resultdir, str(i + 1) + "_" + name_class + "_acc" + str(max_heatmaps[idx]) + ".jpg")
                save_map(heatmaps_values[idx], resultfname, img_original_size)
                print("heatmap saved at", resultfname)

        else:
            for upsampling_factor in range (min_upsampling_factor, max_upsampling_factor):
                img_size = (trained_img_size * upsampling_factor, trained_img_size * upsampling_factor)
                input_image = image.load_img(input_filename, target_size=img_size)
                input_image = image.img_to_array(input_image)
                input_image_expandedim = np.expand_dims(input_image, axis=0)
                input_preprocessed_image = preprocess_input(input_image_expandedim)

                preds = model.predict(input_preprocessed_image)
                print("input img shape (height, width)", input_image.shape, "preds shape", preds.shape)

                heatmaps_values = [preds[0, :, :, i] for i in range(101)]
                max_heatmaps = np.amax(heatmaps_values, axis=(1,2))
                top_n_idx = np.argsort(max_heatmaps)[-top_n_show:][::-1]

                resultdir = os.path.join(os.getcwd(), "results", names[MODELNAME], input_class + "_" + input_instance, "upsampled" + str(upsampling_factor) + "-heatmaps")
                if (os.path.isdir(resultdir)):
                    print("Deleting older version of the folder " + resultdir)
                    shutil.rmtree(resultdir)
                os.makedirs(resultdir)

                save_map(input_filename, os.path.join(resultdir, input_class + "_" + input_instance + ".jpg"), img_size, tick_interval=trained_img_size, is_input_img=True)
                for i, idx in enumerate(top_n_idx):
                    name_class = idx_to_class_name(idx)
                    print("Top", i, "category is: id", idx, ", name", name_class)
                    resultfname = os.path.join(resultdir, str(i + 1) + "_" + name_class + "_acc" + str(max_heatmaps[idx]) + ".jpg")
                    save_map(heatmaps_values[idx], resultfname, img_size, tick_interval=trained_img_size)
                    print("heatmap saved at", resultfname)


                if (max_heatmaps[top_n_idx[0]] >= threshold_accuracy_stop):
                    print("Upsampling step " + str(upsampling_factor) + " finished -> accuracy threshold stop detected (accuracy: " + str(max_heatmaps[top_n_idx[0]]) + ")\n")
                    #  break
                else:
                    print("Upsampling step " + str(upsampling_factor) + " finished -> low accuracy, continuing... (accuracy: " + str(max_heatmaps[top_n_idx[0]]) + ")\n")

            # ---------------------------------------------------------------------------
            # wrong way to get the most probable category
            # summed_heatmaps = np.sum(heatmaps_values, axis=(1, 2))
            # idx_classmax = np.argmax(summed_heatmaps).astype(int)
    else:
        print ("The specified image " + input_filename + " does not exist")