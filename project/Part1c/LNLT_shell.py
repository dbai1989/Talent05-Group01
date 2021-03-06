import argparse
import json
from collections import OrderedDict
import matplotlib.pyplot as plt
import numpy as np
from PairingPotential import PairingPotential
from JClass import JClass  # Noam's Jsqaured
from ReadMatrixElementsFile import ReadMatrixElementsFile
from SPSGenerator import SPSGenerator
from TwoBodyOperator import TwoBodyOperator
from hamiltonian_unperturbed import hamiltonian_unperturbed, hamiltonian_unperturbed_pairing
from LevelPloter import LevelPloter
from ResultPrinter import ResultPrinter
from JSquaredOperator import JSquaredOperator  # Tor's Jsquared
from NumberOperatorSquare import NumberOperatorSquare
from OccupationNumber import occupation
from ShellOutput import shell_output
from NucleusManager import NucleusManager


np.set_printoptions(threshold='nan')



def shell_configurations():
    return [{'name': '0s1/2', 'N': 0},
            {'name': '0p3/2', 'N': 1},
            {'name': '0p1/2', 'N': 1},
            {'name': '0d5/2', 'N': 2},
            {'name': '1s1/2', 'N': 2},
            {'name': '0d3/2', 'N': 2},
            {'name': '0f7/2', 'N': 3},
            {'name': '1p3/2', 'N': 3},
            {'name': '0f5/2', 'N': 3},
            {'name': '1p1/2', 'N': 3},
            {'name': '0g9/2', 'N': 4}]

#################### Argparse ####################
parser = argparse.ArgumentParser(description='Input for shell-model program')
group = parser.add_mutually_exclusive_group()
parser.add_argument('-n','--num_of_particles', help='the number of valence nucleons.', default=2, type=int, required=True)
parser.add_argument('-M','--M_total', help='the total M value for constructing an m-scheme basis.', default=0, type=int, required=False, nargs='*')
parser.add_argument('-os','--orbits_separation', help='in case we choose an orbits file, choose also whether to have '
                                                      'separation of orbits in the m-scheme or not. Used only when -of '
                                                      'is used', default=False, type=bool, required=False)
group.add_argument('-if','--interaction_file', help='interaction file name.', default=False, type=str, required=False)
group.add_argument('-of','--orbits_file', help='json file name for defining the wanted orbits.', default=False, type=str, required=False)
parser.add_argument('-o','--output_file',help='specify output file',default='\dev\null',type=str,required=False)
parser.add_argument('-nu','--nushellx_folder',help='specify nushellx lpt directory to compare our results to',default='\dev\null',type=str,required=False)
parser.add_argument('-Z','--protons_number',help='the number of protons',default=16,type=int,required=False)
args = parser.parse_args()
#################### Argparse ####################



sps_object = SPSGenerator()
shell_configurations_list = shell_configurations()
#folder_name = 'input_files/'  # Folder of input files. # Just in the way

shell_list = [] 

if args.orbits_file:
    #with open("".join((folder_name, args.orbits_file)), 'rb') as data_file:
    with open(args.orbits_file, 'rb') as data_file:
        orbits_dict = json.load(data_file)["shell-orbit P-levels"]
        orbits_dict = OrderedDict(sorted(orbits_dict.iteritems(), key=lambda x: x[0]))  # A sorted dictionary.
                                                                                        # Keys are the "p-levels" (the index of the orbit)
                                                                                        # and values several parameters (see file itself).
    sps_object.calc_sps_list(shell_configurations_list, orbits_dict)
    sps_list = sps_object.get_sps_list()
    shell_list = sps_object.get_shell_list()
    V = PairingPotential(1)

else:
    #interaction_file = open("".join((folder_name, args.interaction_file)), 'rb')
    interaction_file = open(args.interaction_file, 'rb')
    # Read the potential
    V = ReadMatrixElementsFile(interaction_file)
    V.read_file_sps()
    V.read_file_interaction()
    sps_list = V.get_sps_list()
    def comp_shell(a,b):
        return a.get_n() == b.get_n() and a.get_l() == b.get_l() and a.get_j() == b.get_j()
    for current in sps_list:
        if not any([comp_shell(current,sh) for sh in shell_list]):
            shell_list.append(current)



            
sps_object.calc_m_broken_basis(sps_list, args.num_of_particles)
m_broken_basis = sps_object.get_m_broken_basis()

# Calculate the m_scheme_basis according to whether we have a matrix elements input file or a json orbits file.
if args.M_total:
    if args.orbits_file:
        sps_object.calc_m_scheme_basis(m_broken_basis, args.M_total, orbits_dict, args.orbits_separation)
        m_scheme_basis = sps_object.get_m_scheme_basis()
    else:
        sps_object.calc_m_scheme_basis_no_orbit_separation(m_broken_basis, args.M_total)

    m_scheme_basis = sps_object.get_m_scheme_basis()
else:
    m_scheme_basis = np.array(m_broken_basis)
sps_object.set_sps_list(sps_list)



tbi = TwoBodyOperator(sps_list, m_scheme_basis, V)
tbi.compute_matrix()

print("Computes unperturbed hamiltonain")
if args.orbits_file:
    H0=hamiltonian_unperturbed_pairing(m_scheme_basis)
else:
    H0 = hamiltonian_unperturbed(m_scheme_basis, V.get_sp_energies())


HI = tbi.get_matrix()
if np.sum(np.sum(np.abs(HI - np.transpose(HI))))>1e-10:
    print("Interaction hamiltonian is not symmetric")
    exit(1)
factor = (18.0/(16.0+args.num_of_particles))**0.3
if args.orbits_file:
    factor =1
H=H0+factor*HI

energies, eig_vectors_list = np.linalg.eig(np.array(H))
energyzip=[]
for i,e in enumerate(energies):
    energyzip.append((e,eig_vectors_list[:,i]))

#energyzip = zip(energies.tolist(),eig_vectors_list.tolist())
energyzip = sorted(energyzip,key=lambda k: k[0])
en,ev =zip(*energyzip)
energies = list(en)
eig_vectors_list = list(ev)


# Setting up and compute the relevant J**2 matrix
jjop = JSquaredOperator()
jjopmb = TwoBodyOperator(sps_list,m_scheme_basis,jjop)
jjopmb.compute_matrix()
jjop1bmat = jjop.get_single_body_contribution(m_scheme_basis)
jjopmat = jjopmb.get_matrix()
# The last term is to compensate for that J^2 has a two body and a one body term
jjopmat=jjopmat-jjop1bmat*(args.num_of_particles-2)

# Identify the corresponding J-tot quantum number to each energy state
# and computes the shell occupation numbers
j_list = []
occs_all = []
for ev in eig_vectors_list:
    jj = np.dot(ev,np.dot(jjopmat,ev))
    # adds the positive root of the equation J(J+1)=jj
    j_list.append(0.5*(-1+np.sqrt(4*jj+1))) 
    # computes the shell occupation numbers
    occs=[]
    for shell in shell_list:
        occs.append(occupation(shell,ev,m_scheme_basis))
    occs_all.append(occs)

    
# Prints the result
rp = ResultPrinter(energies,
                   j_list,
                   sps_list,
                   m_scheme_basis,
                   args.nushellx_folder,
                   args.num_of_particles,
                   args.protons_number,
                   occs_all)
rp.print_all_to_screen()
if args.output_file:
    rp.print_all_to_file(args.output_file)
