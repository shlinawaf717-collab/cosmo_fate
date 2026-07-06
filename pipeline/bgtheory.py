"""Custom background theory for the F_param axis.

Provides angular_diameter_distance / Hubble / rdrag to cobaya's SN & BAO
likelihoods for arbitrary w(a) parametrizations (pipeline.wparams.MODELS).
Distances computed on an internal grid; rdrag delegated to camb background
(drag-epoch physics is DE-independent at our accuracy; standard practice).

Validation gate: 'cpl' through this class must reproduce the camb-PPF D0
posterior before any new parametrization is trusted (machinery swap, same answer).
"""

import numpy as np
from cobaya.theory import Theory

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.wparams import MODELS, make_ln_fde
from pipeline.cmb_distprior import predict_R_lA_generic

C_KMS = 299792.458
TCMB = 2.7255
NEFF = 3.044
OMEGA_R_H2 = 2.4729e-5 * (1.0 + 0.2271 * NEFF)
MNU_OMH2 = 0.06 / 93.14

_ZGRID = np.concatenate([np.linspace(0, 3.0, 1200)[1:],
                         np.geomspace(3.0, 1300.0, 800)[1:],
                         np.geomspace(1300.0, 1.0e9, 600)[1:]])
_ZGRID = np.concatenate([[0.0], _ZGRID])


class BackgroundW(Theory):
    model: str = 'cpl'

    def initialize(self):
        self.mp = MODELS[self.model]['params']
        self._rdrag_cache = {}

    def get_requirements(self):
        base = ['ombh2', 'omegam', 'H0']
        return {p: None for p in base + self.mp}

    def get_can_provide(self):
        return ['angular_diameter_distance', 'Hubble', 'comoving_radial_distance', 'chen_RlA']

    def get_can_provide_params(self):
        return ['rdrag', 'omk']

    def must_provide(self, **requirements):
        return {}

    def _rdrag(self, ombh2, omch2, H0):
        key = (round(ombh2, 6), round(omch2, 6), round(H0, 4))
        if key not in self._rdrag_cache:
            import camb
            if len(self._rdrag_cache) > 20000:
                self._rdrag_cache.clear()
            pars = camb.set_params(ombh2=ombh2, omch2=omch2, H0=H0, mnu=0.06,
                                   nnu=NEFF, num_massive_neutrinos=1, tau=0.054,
                                   As=2.1e-9, ns=0.9649)
            self._rdrag_cache[key] = camb.get_background(pars).get_derived_params()['rdrag']
        return self._rdrag_cache[key]

    def calculate(self, state, want_derived=True, **params):
        p = self.provider.get_param
        ombh2, om, H0 = p('ombh2'), p('omegam'), p('H0')
        h2 = (H0 / 100.0) ** 2
        omr = OMEGA_R_H2 / h2
        ode = 1.0 - om - omr
        mpars = {k: p(k) for k in self.mp}
        ln_fde = make_ln_fde(self.model, mpars)

        a = 1.0 / (1.0 + _ZGRID)
        lf = ln_fde(a)
        fde = np.exp(np.clip(lf, -700, 700))
        E = np.sqrt(omr * (1 + _ZGRID) ** 4 + om * (1 + _ZGRID) ** 3 + ode * fde)
        H = H0 * E  # km/s/Mpc
        # comoving distance via cumulative trapezoid
        integ = C_KMS / H
        chi = np.concatenate([[0.0], np.cumsum(0.5 * (integ[1:] + integ[:-1])
                                               * np.diff(_ZGRID))])
        omch2 = om * h2 - ombh2 - MNU_OMH2
        state['H'] = H
        state['chi'] = chi
        state['chen_RlA'] = predict_R_lA_generic(ombh2, om, H0, ln_fde)
        state['derived'] = {'rdrag': self._rdrag(ombh2, omch2, H0), 'omk': 0.0}
        return True

    def get_angular_diameter_distance(self, z):
        z = np.atleast_1d(z)
        chi = np.interp(z, _ZGRID, self.current_state['chi'])
        return chi / (1.0 + z)

    def get_comoving_radial_distance(self, z):
        return np.interp(np.atleast_1d(z), _ZGRID, self.current_state['chi'])

    def get_Hubble(self, z, units='km/s/Mpc'):
        H = np.interp(np.atleast_1d(z), _ZGRID, self.current_state['H'])
        if units == '1/Mpc':
            return H / C_KMS
        return H

    def get_chen_RlA(self):
        return self.current_state['chen_RlA']
