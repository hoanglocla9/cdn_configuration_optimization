from argparse import ArgumentParser
from multiprocessing import Process, Queue, cpu_count
import os, signal
from time import time



def main():
    parser = ArgumentParser()
    parser.add_argument('--algo', type=str, default='nsga2', help='number of different seeds')
    parser.add_argument('--n-seed', type=int, default=10, help='number of different seeds')
    args = parser.parse_args()

    start_time = time()

    for seed in range(args.n_seed):
        if args.algo == 'nsga2':
            command = f'python3 nsga2.py --seed {seed}'
        else:
            command = f'python3 bayesian_optimization.py  --seed {seed}'
        ret_code = os.system(command)
        if ret_code == signal.SIGINT:
            exit()
        print(f'Runing {seed} started')
     
    print('all experiments done, time: %.2fs' % (time() - start_time))
    

if __name__ == "__main__":
    main()
