from pymatgen import Element, Composition
import numpy as np

__author__ = 'Anubhav Jain <ajain@lbl.gov>'


def get_mass_list(comp):
    el_mass = []
    el_amt = Composition(comp).get_el_amt_dict()
    for el in el_amt:
        el_mass.append(Element(el).atomic_mass)
    return el_mass


def get_max_min(lst):
    maxmin_dict = {'Max': max(lst), 'Min': min(lst)}
    return maxmin_dict

def get_mean(lst):
    return np.mean(lst)

def get_std(lst):
    return np.std(lst)

def get_med(lst):
    return np.median(lst)

if __name__ == '__main__':
    m = get_mass_list('LiFePO4')
    print m
    m_n = get_max_min(m)
    print m_n
    m_m = get_mean(m)
    print m_m
    m_s = get_std(m)
    print m_s
    m_md = get_med(m)
    print m_md
