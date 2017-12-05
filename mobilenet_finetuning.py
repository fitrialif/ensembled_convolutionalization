import os
import sys
import signal
import time

import keras
from keras.preprocessing.image import ImageDataGenerator
from keras.layers import GlobalAveragePooling2D, Dense, Dropout
from keras.models import Model
from keras.applications.mobilenet import preprocess_input

from lib.plot_utils import save_acc_loss_plots
from lib.randomization import disable_randomization_effects
from lib.callbacks import checkpointer, early_stopper, lr_reducer, csv_logger

disable_randomization_effects()

num_classes = 101
batch_size = 32
IMG_WIDTH = 224
IMG_HEIGHT = 224

train_datagen = ImageDataGenerator(
    horizontal_flip=True,
    preprocessing_function=preprocess_input)

test_datagen = ImageDataGenerator(
    horizontal_flip=True,
    preprocessing_function=preprocess_input)

train_generator = train_datagen.flow_from_directory(
        'dataset-ethz101food/train',
        target_size=(IMG_WIDTH, IMG_HEIGHT),
        batch_size=batch_size,
        class_mode='categorical')

validation_generator = test_datagen.flow_from_directory(
        'dataset-ethz101food/test',
        target_size=(IMG_WIDTH, IMG_HEIGHT),
        batch_size=batch_size,
        class_mode='categorical')

base_model = keras.applications.mobilenet.MobileNet(input_shape=(224, 224, 3), alpha=1.0, depth_multiplier=1, dropout=1e-3, include_top=False, weights='imagenet', input_tensor=None, pooling=None, classes=num_classes)

last_layer = base_model.output
x = GlobalAveragePooling2D()(last_layer)

x = Dense(512, activation='relu', name='fc-1')(x)
x = Dropout(0.5)(x)
x = Dense(256, activation='relu', name='fc-2')(x)
x = Dropout(0.5)(x)
out = Dense(num_classes, activation='softmax', name='output_layer')(x)

custom_model = Model(inputs=base_model.input, outputs=out)
# print(custom_model.summary())


def train_top_n_layers(model, n, epochs, optimizer, callbacks=None, eval_epoch_end=False):
    for i in range(len(model.layers)):
        if i < n:
            model.layers[i].trainable = False
        else:
            model.layers[i].trainable = True

    custom_model.compile(loss='categorical_crossentropy', optimizer=optimizer, metrics=['accuracy'])

    start = time.time()
    history = model.fit_generator(train_generator, steps_per_epoch=75750 // batch_size, epochs=epochs, verbose=1,
                                  validation_data=validation_generator, validation_steps=25250 // batch_size,
                                  callbacks=callbacks, use_multiprocessing=False)
    print('Training time {0:.2f} minutes'.format(-(start - time.time()) / 60))

    if eval_epoch_end:
        (loss, accuracy) = model.evaluate_generator(validation_generator, 250 // 32)
        print("[EVAL] loss={:.4f}, accuracy: {:.4f}%".format(loss, accuracy * 100))
    return history

# filenames
logfile = 'mobilenet_ft_' + time.strftime("%Y-%m-%d_%H-%M-%S") + '.csv'
checkpoints_filename = 'mobilenet_ft_{val_acc:.2f}_{epoch:d}_' + time.strftime("%Y-%m-%d_%H-%M-%S") + '.hdf5'
plot_acc_file = 'mobilenet_ft_acc' + time.strftime("%Y-%m-%d_%H-%M-%S")
plot_loss_file = 'mobilenet_ft_loss' + time.strftime("%Y-%m-%d_%H-%M-%S")

# optimizers
sgd = keras.optimizers.SGD(lr=1e-2, decay=1e-6, momentum=0.9, nesterov=True)
adam = 'adam'

# callbacks to use
stopper = early_stopper(monitor='val_loss', patience=2)
lr_reduce = lr_reducer()
model_saver = checkpointer(checkpoints_filename)
logger = csv_logger(logfile)


def close_signals_handler(signum, frame):
    sys.stdout.flush()
    print('\n\nReceived KeyboardInterrupt (CTRL-C), preparing to exit')
    save_acc_loss_plots(histories,
                        os.path.join(os.getcwd(), 'results', plot_acc_file),
                        os.path.join(os.getcwd(), 'results', plot_loss_file))
    sys.exit(1)


signal.signal(signal.SIGTERM, close_signals_handler)
signal.signal(signal.SIGINT, close_signals_handler)

histories = []
train_time = time.time()
histories.append(train_top_n_layers(custom_model, 6, 5000, adam, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 18, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 24, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 30, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 36, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 42, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 48, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 54, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 60, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 66, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 72, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 78, 2000, sgd, [stopper, logger]))
histories.append(train_top_n_layers(custom_model, 84, 2000, sgd, [stopper, logger, model_saver]))
print('Total training time {0:.2f} minutes'.format(-(train_time - time.time()) / 60))

save_acc_loss_plots(histories,
                    os.path.join(os.getcwd(), 'results', plot_acc_file),
                    os.path.join(os.getcwd(), 'results', plot_loss_file))
