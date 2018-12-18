#!/usr/bin/env python3

import os, sys, json, argparse, glob, shutil
import numpy as np
import scipy.constants as pc

import einstein
import hti
import lib.lmp as lmp

def _main ():
    parser = argparse.ArgumentParser(
        description="Compute free energy by Hamiltonian TI")
    subparsers = parser.add_subparsers(title='Valid subcommands', dest='command')

    parser_gen = subparsers.add_parser('gen', help='Generate a job')
    parser_gen.add_argument('PARAM', type=str ,
                            help='json parameter file')
    parser_gen.add_argument('-o','--output', type=str, default = 'new_job',
                            help='the output folder for the job')

    parser_comp = subparsers.add_parser('compute', help= 'Compute the result of a job')
    parser_comp.add_argument('JOB', type=str ,
                             help='folder of the job')
    parser_comp.add_argument('-t','--type', type=str, default = 'helmholtz', 
                             choices=['helmholtz', 'gibbs'], 
                             help='the type of free energy')
    args = parser.parse_args()

    if args.command is None :
        parser.print_help()
        exit
    if args.command == 'gen' :
        output = args.output
        jdata = json.load(open(args.PARAM, 'r'))
        hti.make_tasks(output, jdata, 'einstein', 'all')
    elif args.command == 'compute' :
        job = args.JOB
        jdata = json.load(open(os.path.join(job, 'in.json'), 'r'))
        fp_conf = open(os.path.join(args.JOB, 'conf.lmp'))
        sys_data = lmp.to_system_data(fp_conf.read().split('\n'))
        natoms = sum(sys_data['atom_numbs'])
        if 'copies' in jdata :
            natoms *= np.prod(jdata['copies'])
        nmols = natoms // 3
        de, de_err, thermo_info = hti.post_tasks(job, jdata, natoms = nmols)
        hti.print_thermo_info(thermo_info)
        if 'reference' not in jdata :
            jdata['reference'] = 'einstein'
        if jdata['reference'] == 'einstein' :
            # e0 normalized by natoms, *3 to nmols
            e0 = einstein.free_energy(jdata) * 3
            print('# free ener of Einstein Mole: %20.8f' % e0)
        else :
            raise RuntimeError("hti_ice should be used with reference einstein")
        print_format = '%20.12f  %10.3e  %10.3e'
        if args.type == 'helmholtz' :
            print('# Helmholtz free ener per mol (stat_err inte_err) [eV]:')
            print(print_format % (e0 + de, de_err[0], de_err[1]))
        if args.type == 'gibbs' :
            pv = thermo_info['pv']
            pv_err = thermo_info['pv_err']
            e1 = e0 + de + pv
            e1_err = np.sqrt(de_err[0]**2 + pv_err**2)
            print('# Gibbs free ener per mol (stat_err inte_err) [eV]:')
            print(print_format % (e1, e1_err, de_err[1]))


if __name__ == '__main__' :
    _main()