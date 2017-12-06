"""
    learn.py

    defines functions that train a model based on 
    movie data collected in scrape.py

    TODO: visualize which features are important, 
                    which neurons fire on what input,
          cross-validation on training
"""
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelBinarizer, Imputer, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import KFold
from CategoricalEncoder import CategoricalEncoder
from sklearn.metrics import explained_variance_score, r2_score
                        # model performance metrics
from glob import glob   # used to create list of filenames from wildcard
import os.path          # used to check if a file exists
import pickle           # used for object serialization
import random           # used to split the data
import pandas as pd
import numpy as np

# local imports
from scrape import json_print, writeToFile, readFromFile
from clean_data import shapeDatum

def loadData(*sections):
    """ loads data from data-stores/ dir and returns it.  lots of data  """
    data = []

    if sections == ():
        files = glob("data-stores/m_data_*.pkl")
    else: 
        files = ["data-stores/m_data_{}.pkl".format(i) for i in sections]
        files = list(filter(lambda fn: os.path.isfile(fn), files))

    print("datafiles available:", files)
    for f in files:
        with open(f, 'rb') as handle:
            data += pickle.load(handle)

    return data

def flattenListValues(data):
    # turn columns with list values into multiple binary columns
    # answered here: https://stackoverflow.com/a/47535706/3972042
    df = pd.DataFrame(data)

    # genres
    # explode the list to separate rows
    X = pd.concat(
            [pd.DataFrame(v, index=np.repeat(k,len(v)), columns=['genre']) 
                                    for k,v in df.genre.to_dict().items()])
    lb = LabelBinarizer()
    dd = pd.DataFrame(lb.fit_transform(X), index=X.index, columns=lb.classes_)
    del df['genre']
    df = pd.concat([df, dd.groupby(dd.index).max()], axis=1)

    # languages
    # explode the list to separate rows
    X = pd.concat(
            [pd.DataFrame(v, index=np.repeat(k,len(v)), columns=['language']) 
                                    for k,v in df.language.to_dict().items()])
    lb = LabelBinarizer()
    dd = pd.DataFrame(lb.fit_transform(X), index=X.index, columns=lb.classes_)
    del df['language']
    df = pd.concat([df, dd.groupby(dd.index).max()], axis=1)

    # production
    # explode the list to separate rows
    X = pd.concat(
            [pd.DataFrame(v, index=np.repeat(k,len(v)), columns=['production']) 
                                    for k,v in df.production.to_dict().items()])
    lb = LabelBinarizer()
    dd = pd.DataFrame(lb.fit_transform(X), index=X.index, columns=lb.classes_)
    del df['production']
    df = pd.concat([df, dd.groupby(dd.index).max()], axis=1)

    # countries
    # explode the list to separate rows
    X = pd.concat(
            [pd.DataFrame(v, index=np.repeat(k,len(v)), columns=['country']) 
                                    for k,v in df.country.to_dict().items()])
    lb = LabelBinarizer()
    dd = pd.DataFrame(lb.fit_transform(X), index=X.index, columns=lb.classes_)
    del df['country']
    df = pd.concat([df, dd.groupby(dd.index).max()], axis=1)

    return df

def shapeData(data):
    """ takes the data loaded from file and returns training data and labels
        that can easily be processed by machine learning """

    shapedData = [shapeDatum(row) for row in data]
    removed = [x[0] for x in shapedData if "Err" in x[0]]
    print("shapeDatum removed {} rows of data.".format(len(removed)))
    data, labels = zip(*[row for row in shapedData if "Err" not in row[0]])
                            
    df = flattenListValues(list(data))
    writeToFile((df, list(labels)), "cleanedData.pkl")

    # return a list of the data values and the label
    return (df.values.tolist(), list(labels))

def splitData(data, labels, ratio=0.5):
    """ splits the data into training and test sets returned in the format 
        ( (training data, training labels), (test data, test labels) )"""
    assert(len(data) == len(labels))

    test = []
    testlabels = []
    len_test = round(len(data) * (1 - ratio))

    # randomly select an entry from the data to be moved into the test set
    for _ in range(len_test):
        i = random.randrange(len(data))
        test.append(data.pop(i))
        testlabels.append(labels.pop(i))

    return ( (data, labels), (test, testlabels) )

def crossValTrain(data, labels, nFolds, model):
    """ 
        split the data and labels into n groups, and train the model on 
        all but one of the groups, and return the accuracy for each round
    """
    # split the data into n groups

    # for group in groups:
    #   model.train(allothergroups)
    #   model.test(group)
    #   results.append(model.accuracy)
    # return results

def initModel(L, F, R):
    """ uses sklearn pipeline to initialize an AI model """
    cat_indices = [7, 9, 12]

    return Pipeline(steps=
            [("ce", CategoricalEncoder(cat_indices)),
             ("imp", Imputer()),
             ("mmscaler", MinMaxScaler()),
             ("pca", PCA()),
             ("nn", MLPRegressor(hidden_layer_sizes=L, max_iter=2500))])
             #("nn", MLPRegressor(hidden_layer_sizes=L, learning_rate=R,
             #                   activation=F, max_iter=2500))])


def saveModel(model, filename):
    with open(filename, 'wb') as handle:
        pickle.dump(model, handle, protocol=pickle.HIGHEST_PROTOCOL)

def main():
    # load and process the data
    data = loadData()
    print("Loaded", len(data), "rows of data.")
    training, labels = shapeData(data)
    print("Shaved data down to {} rows with {} labels."
                .format(len(training), len(labels)))

    labels = np.array(labels).reshape(-1, 1)
    mmscaler = MinMaxScaler()
    labels = [l[0] for l in mmscaler.fit_transform(labels)]

    #writeToFile((training, labels), "cleanData.pkl")

    # TODO use mmscaler.inverse_transform to compare to test labels

    # TODO replace this split data with kfold
    #   kf = KFold(n_folds=10)
    #   train, test = kf.split(training, labels)

    #training = training[:,:1000]

    train, test = splitData(training, labels, .9)
    print("Split data into {} training rows and {} test rows."
                .format(len(train[0]), len(test[0])))

    # separate variables for different sections of data
    train_X, train_Y = train
    test_X, test_Y = test

    print(len(train_X), "by", len(train_X[0]))

    for f in range(40, 60):
        # create and train the model
        model = initModel((f), 'logistic', 'adaptive')
        model.fit(train_X, train_Y)

        # test the model and report accuracy
        pred_Y = model.predict(test_X)
        deltas = [abs(p-l) for p, l in zip(pred_Y, test_Y)]
        #print(" hidden layers:  (" + str(h) + ", " + str(i) + ")")
        print("len(hidden layer):  ", f)
        print("        avg delta:  ", sum(deltas)/len(deltas))
        #print("variance score:  ", explained_variance_score(test_Y, pred_Y))
        #print("     r squared:  ", r2_score(test_Y, pred_Y))

        #saveModel(model, "model.pkl")

if __name__ == "__main__":
    main()
