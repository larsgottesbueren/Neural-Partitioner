import matplotlib.pyplot as plt
import time
import torch
import argparse


### DEFAULT PARAMETERS ###

N_BINS = 16
N_HIDDEN = 128
N_EPOCHS = 80
LR = 1e-3
K = 10
DATASET_NAME = 'sift'
BATCH_SIZE = 2048
N_BINS_TO_SEARCH = 2
N_TREES = 2
N_LEVELS = 0
TREE_BRANCHING = 1
MODEL_TYPE = 'neural'

cpu = torch.device('cpu')
cuda = torch.device('cuda')
if torch.cuda.is_available():
    primary_device = cuda
    secondary_device = cpu
else:
    primary_device = cpu
    secondary_device = cpu




def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n_bins', default=N_BINS, type=int, help='number of bins' )
    parser.add_argument('--k_train', default=K, type=int, help='number of neighbors during training')
    parser.add_argument('--k_test', default=K, type=int, help='number of neighbors to construct knn graph')
    parser.add_argument('--dataset_name', default=DATASET_NAME, type=str, help='Specify dataset name, can be one of "sift", "mnist"')
    parser.add_argument('--n_hidden', default=N_HIDDEN, type=int, help='hidden dimension')
    parser.add_argument('--n_epochs', default=N_EPOCHS, type=int, help='number of epochs for training')
    parser.add_argument('--lr', default=LR, type=float, help='learning rate')    
    parser.add_argument('--batch_size', default=BATCH_SIZE, type=int, help='batch size')
    parser.add_argument('--n_bins_to_search', default=N_BINS_TO_SEARCH, type=int, help='number of bins to use')
    parser.add_argument('--n_trees', default=N_TREES, type=int, help='number of trees')
    parser.add_argument('--n_levels', default=N_LEVELS, type=int, help='number of levels in tree')
    parser.add_argument('--tree_branching', default=TREE_BRANCHING, type=int, help='number of children per node in tree')
    parser.add_argument('--model_type', default=MODEL_TYPE, type=str, help='Type of model to use')
    parser.add_argument('--load_knn', action='store_true', help='Load existing k-NN matrix from file')
    parser.add_argument('--continue_train', action='store_true', help='Load existing models from file')


    opt = parser.parse_args()
    if opt.dataset_name not in ['sift','mnist','glove']:
        raise ValueError('dataset_name must be one of "sift", "mnist"')

    if opt.model_type not in ['neural', 'linear']:
        raise ValueError('model_type must be one of "neural", "linear"')
        
    return opt 




def get_test_accuracy(model_forest, knn, X_test, k, batch_size=1024, bin_count_param=1, models_path=None):

    

    if models_path == None:
        print('no file directory for models found')
        return
    # assert isinstance(root_model, Model)

    


    print('-----DOING MODEL INFERENCE ------- ')

    part_printed = False
    for my_batch_size in [16000]:
        t1 = time.time()
        query_bins, scores, dataset_bins = model_forest.infer(X_test, my_batch_size, bin_count_param, models_path)
        t2 = time.time()
        print("Inference with batch size", my_batch_size, "took", (t2-t1), "seconds for", len(X_test), "queries", "That's", 1000*(t2-t1)/(len(X_test)), "ms per query")

        if not part_printed:
            print(query_bins.shape, dataset_bins.shape)
            part_printed = True
            with open('neural-clusters.txt', 'w') as f:
                for db in dataset_bins[0]:
                    for x in db:
                        f.write(str(x) + ' ')
                    f.write('\n')
            with open('neural-routes.txt', 'w') as f:
                f.write('1\nR\nUSP USP 0 250 22 true 10000 22 64 350\n')
                
                for qb in query_bins[0]:
                    for x in qb:
                        f.write(str(x) + ' ')
                    f.write('\n')
   

    print('----- MODEL INFERENCE DONE ------- ')


    n_q = query_bins.shape[1] # no of points in test set only

    print ("num queries = ", n_q)

    exit()

    all_points_bins = []

    ensemble_accuracies = [] # array of accuracies
    ensemble_cand_set_sizes = []

    single_model = model_forest.trees[0].root.model

    print('no of parameters in one model: {}'.format(sum(p.numel() for p in single_model.parameters())))

    n_trees = model_forest.n_trees

    del model_forest

    torch.cuda.empty_cache()

    running_time = 0.0

    print('----- CALCULATING K-NN RECALL FOR EACH POINT ------- ')

    for num_models in range(n_trees):
    # for num_models in range(n_trees- 1, n_trees): # TAKING ALL TREES AT ONCE

        accuracies = []
        
        X = []

    
        for bin_count in range(1, bin_count_param + 1, 1):

         
        
            num_knns = torch.randn(n_q, 1)
            candidate_set_sizes = torch.randn(n_q, 1)


            print("%d models, %d bins "%(num_models + 1, bin_count))
            print()

            running_time = 0.0


            for point in range(n_q):
                c2_time = time.time()

                max_i = -1
               

                max_i = torch.argmax(scores[:(num_models+1)], 0)[point].flatten()

                assigned_bins = query_bins[max_i, point, :].flatten()

                all_points_bins.append(assigned_bins[0].item())

                candidate_set_points = sum(dataset_bins[max_i].flatten() == b for b in assigned_bins[:bin_count]).nonzero(as_tuple=False).flatten()




                c3_time = time.time()
                t2_time = c3_time - c2_time
                running_time += t2_time

                # FIND CANDIDATE SET OF QUERY POINT END
                candidate_set_size = candidate_set_points.shape[0]
                knn_points = knn[point][:k] # choose first k points for testing
                knn_points_size = knn_points.shape[0]


                # find size of overlap between knn_points and bin_points

                
                knn_and_bin_points = torch.cat((candidate_set_points, knn_points))
                
                uniques = torch.unique(knn_and_bin_points)

                uniques_size = uniques.shape[0]

                overlap = candidate_set_size + knn_points_size - uniques_size

                num_knns[point] = overlap
                
                candidate_set_sizes[point] = candidate_set_size
           
                
                
            pass

            

            accuracy = num_knns / k
            print()

            accuracy = torch.mean(accuracy)

            print('mean accuracy ', accuracy)
            print('running time', running_time)
            candidate_set_size = torch.mean(candidate_set_sizes)
            print("mean candidate set size", candidate_set_size)
            print()

            accuracies.append(accuracy.item()) # for each bin_count

            X.append(candidate_set_size.item())
        pass
        ensemble_accuracies.append(accuracies)
        ensemble_cand_set_sizes.append(X)



    if bin_count_param > 0:

        print("first bin accuracy")
        print(accuracies[0])

        print("candidate_set_size of first bin on average")
        print(X[0])

        for m, acc in enumerate(ensemble_accuracies):
            
            plt.plot(ensemble_cand_set_sizes[m], acc, label="no of models: " + str(m+1))
        plt.legend()
        plt.title("Average k-NN Recall vs Candidate Set Size")
        plt.show()

    return all_points_bins, ensemble_cand_set_sizes, ensemble_accuracies
