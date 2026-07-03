# MIOST method brief — the multiscale-inversion family (Ubelmann 2021 / Ubelmann 2022 / Ballarotta 2023)

**Date:** 2026-07-02
**Purpose:** a faithful, verifiable account of the MIOST method family, extracted from
the three local PDFs in `docs/papers/`, to serve as the basis for a *later* design
session on implementing MIOST as a sverdrup method scored on the 2021a harness. This
brief contains **no design and no sverdrup integration**.
**Scope (owner-confirmed 2026-07-02):** the implementation target is the **minimal
mesoscale, altimetry-only SSH configuration** — the single-component multiscale
inversion that matches sverdrup's 2021a Gulf Stream target. Internal tides, equatorial
waves, Doppler currents, and drifters are out of scope initially; each gets a
half-page inventory section (§4) but no deep extraction.

**Sources** (the only sources used; no external material):

- **U2021** — Ubelmann, Dibarboure, Gaultier, Ponte, Ardhuin, Ballarotta, Faugère,
  *Reconstructing Ocean Surface Current Combining Altimetry and Future Spaceborne
  Doppler Data*, JGR: Oceans 126, e2020JC016560 (2021). PDF pages = printed pages.
- **U2022** — Ubelmann, Carrere, Pujol, Ballarotta, Faugère, Dibarboure et al.,
  *Simultaneous estimation of ocean mesoscale and coherent internal tide sea surface
  height signatures from the global altimetry record*, Ocean Science 18, 469–481
  (2022). PDF page N = printed page 468+N; citations below use **PDF** pages.
- **B2023** — Ballarotta, Ubelmann et al., *Improved global sea surface height and
  current maps from remote sensing and in situ observations*, ESSD 15, 295–315 (2023).
  PDF page N = printed page 294+N; citations below use **PDF** pages.

**Conventions.** Every load-bearing claim carries (paper, section/equation/figure,
page). Claims are **DOCUMENTED** (in the papers) unless a block is explicitly marked
**INFERENCE** or **ANALYSIS** (mine, not the papers'). Gaps are flagged, not filled.
Extraction provenance is in §10.

---

## 1. One family, three papers — where each piece of the core is documented

These are stages of one evolving method, not three methods. Where the core machinery
actually lives:

| Core piece | Primary documentation | Restated/refined in |
|---|---|---|
| Linear-Gaussian setup, OI ↔ SMW duality | U2021 §2.1, Eqs. 1–3, p.2 | U2022 §2.1, Eqs. 1–3, p.2; B2023 App. A1–A2, Eq. A7, p.17 |
| Multi-component state, reduced basis, `B_k = Γ_k Q_k Γ_kᵀ` | U2021 §2.3.1, Eqs. 10–16, pp.4–5 | U2022 §3.2, Eqs. 6–10, pp.4–5; B2023 App. A2, Eqs. A8–A14, pp.17–18 |
| **Mesoscale/geostrophy wavelet basis (the analytical formula)** | U2021 §2.3.2.1, Eqs. 18–20, p.6 | B2023 App. A2.1, Eqs. A15–A18, pp.18–19 (U2022 §3.2.1 p.5 explicitly defers: "the analytical formula … is given" in U2021) |
| Q filled from an altimetry SSH spectrum | U2021 p.6 prose | U2022 §3.2.1 p.5 prose (AltiKa database); B2023 App. A2.1 p.19 prose |
| Solver (matrix-free PCG on the reduced normal equations) | U2021 §2.3.1, p.5 prose | U2022 §3.2.3, Eq. 13 + p.7 ("typically 100 iterations"); B2023 App. A2, p.18 |
| **Global tiling / domain decomposition** | **U2022 §3.2.3, p.7 (only place it is documented)** | — |
| Obs preprocessing for a real-data global run | U2022 §3.1, p.4 | B2023 §2.1, pp.2–4 (operational product) |
| Altimetry-only, geostrophy-only experiment vs DUACS | — | B2023 Table 3 ("MIOST allsat-1"), §4, Tables 4–5 |

Naming note (DOCUMENTED): the string "MIOST" appears nowhere in U2021 — the paper does
not name its method. U2022 and B2023 use "MIOST" and cite U2021 as the method paper
(U2022 §3.2 p.4; B2023 §2.2 p.4). The identification "U2021 = MIOST" is the later
papers' attribution, not U2021's own.

---

## 2. The core method (minimal mesoscale altimetry-only configuration)

### 2.1 Estimation problem and state decomposition

DOCUMENTED. The state is an extended vector of N physical components assumed mutually
independent: `x = (x_1ᵀ, …, x_Nᵀ)ᵀ` (U2021 Eq. 10, p.4; U2022 Eq. 1, p.2; B2023
Eq. A8, p.17). Observations see the sum: `y = Σ_k H_k x_k + ε` (U2022 Eq. 1, p.2).
Independence across components makes the prior block-diagonal: `B =
blockdiag(B_1,…,B_N)` (U2022 Eq. 3, p.2). In U2021/B2023 each component is
multivariate on the grid — `x_k = (h_kᵀ, u_kᵀ, v_kᵀ)ᵀ` (SSH + currents; U2021 p.4;
B2023 Eq. A8 discussion, p.17) — with blocks zeroed where a component contributes
nothing (U2021 pp.4–5).

**Minimal-core reading (DOCUMENTED):** for the altimetry-only mesoscale configuration
the state is a *single* component — "geostrophy" in the papers' vocabulary (U2021
§2.3.2, p.5, component 1; B2023 App. A2, p.17, component 1) — and the SSH block is the
only one exercised by altimetry observations. B2023's "MIOST allsat-1" experiment
(Table 3, p.7) is exactly this configuration: altimeter data only, geostrophy
component only, no drifters, no equatorial waves.

### 2.2 The reduced basis: wavelet elements

DOCUMENTED. Each component's grid-space state is expanded in a reduced basis:
`x_k = Γ_k η_k` (U2021 Eq. 11, p.4; U2022 Eq. 6, p.4; B2023 Eq. A9, p.17), giving the
equivalent covariance model `B_k = Γ_k Q_k Γ_kᵀ` with **Q_k diagonal** (U2021 Eq. 12,
p.5; U2022 Eq. 10, p.5; B2023 Eq. A10, p.18).

The mesoscale/geostrophy basis element (U2021 Eq. 18, p.6; identically B2023 Eq. A16,
pp.18–19) is a **plane-wave carrier times a compactly supported separable cosine
taper** — not a Gaussian, not a Morlet:

```
Γ_{1,h}[i,p] = cos( k_{x,p}(x_i − x_p) + k_{y,p}(y_i − y_p) + Φ_p )
             · f_tap( (x_i−x_p)/L_{x_p}, (y_i−y_p)/L_{y_p}, (t_i−t_p)/L_{t_p} )

f_tap(δx, δy, δt) = cos(π δx/2)·cos(π δy/2)·cos(π δt/2)   for (|δx|,|δy|,|δt|) < 1
                  = 0 elsewhere                     (U2021 Eq. 19, p.6; B2023 Eq. A17)
```

where p indexes elements centered on a "space–time pavement" (x_p, y_p, t_p), and:

- **Phase pairs:** Φ_p alternates 0 and π/2 — sine/cosine pairs per
  (location, wavevector), giving the fit a phase degree of freedom (U2021 p.6 prose;
  B2023 p.19 prose).
- **Scales:** wavelengths spanning "the mappable mesoscale range" — **80–800 km** in
  the U2021 North Atlantic problem (U2021 p.6, prose: "between 80 km and 800 km …
  spanning in all directions of the plane"); **80–900 km** in the B2023 global product
  (B2023 App. A2.1, p.19: "between 80 and 900 km"). Per-paper difference; neither
  explains the change.
- **Spacing:** "a spacing inversely proportional to the wavelet extensions, allowing
  to represent a signal of any intermediate wavelength" (U2021 p.6; same wording B2023
  p.19). **The numeric spacing (as a fraction of scale, in space, time, and
  wavenumber) is NOT SPECIFIED in any of the three papers.** GAP — load-bearing for
  reimplementation (controls basis size and fidelity of the equivalent covariance).
- **Support:** `L_x = L_y = 1.5 ×` the element's wavelength (U2021 p.6; B2023 p.19:
  "1.5 the wavelength").
- **Directions:** "all directions of the plane" (U2021 p.6). **The number of direction
  samples is NOT SPECIFIED in any paper.** GAP.
- "The ensemble can be seen as a wavelet basis" (U2021 p.6).

Orthogonality: U2022 states the Γ_k are assumed orthogonal, "satisfied by construction
(diagonalizing the state covariances…)" (U2022 §3.2, p.4 prose); no explicit
orthogonalization procedure is given in any paper. Representers `Γ[i,:] Q Γ[j,:]ᵀ`
reproduce "standard shapes of altimetry covariance models with a negative lobe" à la
Le Traon et al. 1998 (U2022 §3.2.1, Fig. 4, pp.5–6; U2021 Fig. 3, pp.6–7).

### 2.3 Time handling / space–time covariance encoding

DOCUMENTED. For the mesoscale component, time is handled **exactly like a third
spatial-taper axis**: each element is local in time through the same compact cosine
taper `cos(π δt/2)` with temporal half-width `L_t` (U2021 Eqs. 18–19, p.6). `L_t` is
set to "the decorrelation time of Aviso maps, around 10 days in this region" (U2021
p.6; U2022 Fig. 3c caption p.5 shows the same "typical time extension of 10 d",
"Gaussian-like shape"; B2023 App. A2.1 p.19 says `L_t` = "the decorrelation timescale"
with **no numeric value** — GAP for the operational product). The space–time
covariance of the equivalent model is therefore encoded per element as a separable
(space × time) compactly supported bump modulated by the spatial plane wave; the
superposition over scales/positions/phases with Q variances produces the full
space–time covariance `B_1 = Γ_1 Q_1 Γ_1ᵀ`.

**No propagation/advection is documented in the mesoscale basis** — no westward-phase
or advected covariance for the geostrophy component in any of the three papers (U2021:
none; U2022: none; B2023: none for geostrophy). Contrast (DOCUMENTED): the classical
DUACS OI covariance that B2023 recalls *does* carry propagation speeds `C_px, C_py`
(B2023 Eqs. A3–A4, p.17), and the equatorial-wave components encode propagation via
`cos(ωt − kx)` carriers (B2023 Eqs. A19–A21, p.19). So within the family, propagation
exists only in wave components, not in the mesoscale basis as documented. Temporal
spacing of pavement centers: NOT SPECIFIED in any paper. GAP.

### 2.4 Prior variances (Q)

DOCUMENTED (thinly). Each element p gets a diagonal prior variance "consistent with
the power spectrum observed from altimetry at the corresponding wavelength with
isotropy assumption" (U2021 p.6; verbatim-equivalent B2023 p.19). U2022 adds the data
source for the global run: "The database of SSH power density spectrum used to fill Q
was built from the AltiKa along-track SSH anomalies" (U2022 §3.2.1, p.5), and notes
geographic variation of element variances (representer asymmetry remark, U2022
pp.5–6). **The spectrum's functional form, binning, geographic parameterization, and
the exact spectrum→variance normalization (how PSD at wavelength λ maps to the
variance of a windowed element, including the sine/cosine pair split) are NOT
SPECIFIED in any paper.** GAP — load-bearing: this is the entire prior amplitude
calibration.

### 2.5 Observation operator

DOCUMENTED. Reduced-space operator `G_k = H_k Γ_k`, `y = G η + ε` (U2021 Eqs. 13–14,
p.5; U2022 Eq. 7, p.4; B2023 Eqs. A11–A12, p.18). H_k is "formally a tri-linear
interpolator" grid→along-track (U2021 §2.2.1 p.3; U2022 p.4 prose: "trilinear
interpolators"), but **G is never assembled through a gridded H**: "each block of G is
directly filled from the analytical expression of the reduced-space elements …
constituting the columns of the matrix" (U2021 p.5; same statement U2022 §3.2.3 step 1
p.7 and B2023 p.18) — i.e. the wavelet formula is evaluated analytically at each
observation's (x, y, t). For altimetry, the obs vector is along-track SSH anomalies;
for the minimal core that is the whole of y. ε covers "instrument error and
representativity"; **R is diagonal** (U2021 §2.2.1/§2.2.2 p.3 for both obs types;
B2023 App. A1 p.17). **Numeric R values for the real-data runs are NOT SPECIFIED in
any paper** (U2022's R is given only for its 1-D synthetic demo, §2.2 pp.2–3; B2023
gives none). GAP.

### 2.6 Estimator (cost function)

DOCUMENTED. **No paper ever writes an explicit cost function J.** The estimator is
stated directly as the linear-Gaussian analysis: OI form `x^a = B Hᵀ (H B Hᵀ +
R)⁻¹ y` (U2021 Eq. 2, p.2 — "known as Optimal Interpolation"; U2022 Eq. 2, p.2), and
its Sherman–Morrison–Woodbury state-space equivalent `x^a = (Hᵀ R⁻¹ H + B⁻¹)⁻¹ Hᵀ R⁻¹
y` (U2021 Eq. 3, p.2; B2023 Eq. A7, p.17). In the reduced space this becomes the
normal equations actually solved:

```
η^a = (Gᵀ R⁻¹ G + Q⁻¹)⁻¹ Gᵀ R⁻¹ y        (U2021 Eq. 15, p.5; U2022 Eq. 13, p.7;
x^a = Γ η^a                                B2023 Eq. A13–A14, p.18; U2021 Eq. 16)
```

(B2023 §2.2 p.4 calls this "a variational approach" in passing; the mathematical
object is the same MAP/BLUE solution.) ANALYSIS (mine): this is exactly the minimizer
of `J(η) = ηᵀQ⁻¹η + (y − Gη)ᵀR⁻¹(y − Gη)`; the papers simply never write it.

### 2.7 Solver

DOCUMENTED. Matrix-free **preconditioned conjugate gradient** on `A η = z` with
`A = Gᵀ R⁻¹ G + Q⁻¹`, `z = Gᵀ R⁻¹ y` computed once; A is never formed — each `Aη`
product is computed "in two steps from a matrix multiplication of G then of Gᵀ"
(U2021 §2.3.1, p.5 prose; restated B2023 App. A2, p.18). Convergence "when Aη
approaches z" (U2021 p.5); "typically 100 iterations" for the global U2022 run (U2022
§3.2.3, p.7). The solution is projected to the output grid sequentially, element by
element, "by summing the analytical expression of the wavelets applied to grid
coordinates … separately for each component k", bypassing storage of Γ (U2021 p.5;
U2022 step 3, p.7).

**The preconditioner is never identified in any of the three papers** — U2021 says
"preconditioned conjugate gradient" and stops; U2022 says "as explained in detail in
Ubelmann et al., 2021" (which does not explain it); B2023 repeats "preconditioned
conjugate gradient". GAP — flagged, not filled. Convergence tolerance and CG variant:
NOT SPECIFIED anywhere.

### 2.8 Computational shape and scaling to global

DOCUMENTED (all of it lives in U2022 §3.2.3, p.7):

- **Tiling:** "The problem is solved on 15 by 15° tiles separately, paving the whole
  globe with 2° overlaps to allow smooth transitions on the final concatenation of the
  solution."
- **Seam treatment:** "a continuous global solution is computed by linearly
  interpolating the solution in the overlapping zones, with a weight ratio
  proportional to the boundary relative distances."
- **Problem sizes (global, 25-yr record):** mesoscale component ~**10⁹ elements**
  globally over 25 years, but G is "extremely sparse" because each element's support
  is local in space *and* time so "very few observation points are included in a given
  element extension" (Fig. 5a); internal-tide components ~10⁷ elements, denser columns
  (local in space, persistent in time; Fig. 5b).
- **Hardware:** "a total memory approaching 2 TB RAM shared by 200 threads" on a
  supercomputer, G segmented with communications at each matrix product.
- **Per-tile element counts, wall-clock time: NOT SPECIFIED.** GAP (minor).

U2021 (regional North Atlantic OSSE) reports **no** domain decomposition — a single
large space–time window (U2021 §2.3, p.4) — and no element counts or timings. B2023
adds nothing computational (its App. A2 restates the solver only). So: for a 2021a
Gulf-Stream-box target, the documented precedent is U2021's single-window regional
solve; the 15°×15°+2°-overlap machinery is only needed at global scale, and only U2022
documents it.

---

## 3. Operational configuration, per paper

Marked per-paper; nothing merged. "NS" = NOT SPECIFIED in that paper.

| Parameter | U2021 (NATL OSSE) | U2022 (global 25-yr altimetry) | B2023 (operational product) |
|---|---|---|---|
| Mesoscale wavelength range | 80–800 km (p.6) | NS (defers to U2021) | 80–900 km (App. A2.1, p.19) |
| Spatial support | 1.5 × wavelength (p.6) | NS (illustration only: 150 km element, Fig. 3) | 1.5 × wavelength (p.19) |
| Temporal half-width L_t | ≈10 d ("decorrelation time of Aviso maps … in this region", p.6) | ~10 d shown in illustration (Fig. 3c, p.5) | "the decorrelation timescale", value NS (p.19) |
| Element spacing | "inversely proportional to the wavelet extensions", numeric NS (p.6) | NS | same wording, numeric NS (p.19) |
| Direction count | NS ("all directions") | NS | NS |
| Q (prior variances) | altimetry power spectrum at element wavelength, isotropic; values NS (p.6) | AltiKa along-track PSD database; form NS (§3.2.1, p.5) | altimetry power spectrum, isotropy assumption; values NS (p.19) |
| Obs-error R | diagonal; SSH values NS; Doppler basic-mapping 0.2² (m/s)² (p.3) | diagonal in 1-D demo only; real-data values NS | "instrument error and representativity"; values NS |
| Input SSH obs | OSSE: 5 nadir altimeters (2 Jason-like + 3 Sentinel-3-like), 1 Hz ≈ 6 km, 3 cm RMS white noise (§3.2.1, p.11) | CMEMS L3 along-track (tailored for DA), all missions 1993-01-01→2017-08-31; 1 Hz (~6 km) averaged 3:1 to 0.33 Hz (~18 km) super-obs (§3.1, p.4) | CMEMS DT2021 L3 (SEALEVEL_GLO_PHY_L3_MY_008_062), 1 Hz (~7 km), **unfiltered SLA** + DAC/ocean-tide/LWE corrections; missions: AltiKa, Envisat, J1–J3, CryoSat-2, HY-2A/B, S3A/B (§2.1.1 p.2, §3.1 p.5); subsampling NS |
| Corrections detail | OSSE (none needed) | NS beyond "same processing (barotropic tidal model in particular)" for validation data (§3.3, p.7) | Eq. 1 (p.2): full environmental+geophysical correction stack; MSS = CNES-CLS18 |
| Output grid | NS | 1/8°, daily (mesoscale); IT as two phase fields at reference date (§3.2.3, p.7) | 0.1°, daily, 80°S–90°N, 2016-07-01→2020-06-30 (§5, p.13) |
| Domain decomposition | none (single window) | 15°×15° tiles, 2° overlap, linear blend (§3.2.3, p.7) | NS (defers) |
| Components in run | geostrophy + 2 LF ageostrophy + NIO (N=4) | mesoscale + internal-tide constituents×modes | geostrophy + TIW + Poincaré (N=3) (Eq. A8, p.17) |

**The 2021a-challenge MIOST configuration is not documented in any of the three
papers** — none of them describes the specific run submitted to the 2021a Gulf Stream
data challenge (see §7). GAP, flagged: the closest documented configurations are
U2021's NATL geostrophy component and B2023's "MIOST allsat-1" experiment.

---

## 4. Out-of-scope components (inventory, half-page each)

### 4.1 Doppler / current reconstruction (U2021) — out of scope

U2021's actual topic: joint SSH + surface-current mapping for the proposed SKIM
Doppler mission. Currents enter two ways. (a) A *basic* benchmark mapping (U2021
§2.2.2, pp.3–4): local bivariate weighted least squares for [u,v] from radial
velocities within a 40 km/10 d Hamming-weighted neighborhood, `[u,v]ᵀ = (HᵀR⁻¹H)⁻¹
HᵀR⁻¹ u_r°` (Eq. 5), H rows `[cos θ_j, sin θ_j]` per azimuth (Eq. 6), R = 0.2²
(m/s)²; needs ≥2 distinct azimuths (Fig. 1, p.4). (b) The *improved* (multiscale)
mapping: radial velocities join the extended obs vector `y = (h°ᵀ, u_r°ᵀ)ᵀ` (p.5), and
every component carries analytic current blocks — for geostrophy, `Γ_{1,u} = −(g/f_c)
∂Γ_{1,h}/∂y`, `Γ_{1,v} = +(g/f_c) ∂Γ_{1,h}/∂x` (Eq. 20, p.6; B2023 Eq. A18 identical,
for drifters), i.e. **geostrophy is encoded on the state side as analytic derivatives
of the SSH wavelet**, not by numerically differentiating maps. Ageostrophic components:
(2) rotational LF via stream-function-like potential P, window-only elements, L=400 km,
5 d (Eqs. 21–23, p.8); (3) divergent LF "exactly the same way" (Eqs. 24–25, pp.8–9);
(4) near-inertial oscillations: slowly varying envelopes A,B times a deterministic
inertial carrier `cos/sin(−2π f_c t)`, envelope = spatial f_tap × Gaussian-like time
decay `e^{−|t|^q/τ^q}`, q=2, τ=3 d, L=250 km (Eqs. 26–28, pp.9–10). Validation is
OSSE-spectral (NATL60 truth): geostrophic effective resolving ≈110 km altimetry-only
vs ≈90 km with SKIM; ~50% of near-inertial variance recovered (Abstract p.1; §4.2
pp.14–17, Figs. 12–13). Relevance to core: proves the multi-component machinery and
supplies the geostrophic-derivative pattern reused for drifters in B2023.

### 4.2 Coherent internal tides (U2022) — out of scope

Components added to the same inversion, one per tidal constituent × vertical mode: M2
and K1 (modes 1+2), S2 and O1 (mode 1) (U2022 abstract p.1; §3.2.2 p.6; K1 dropped
poleward of 30° in the final run, §3.3 p.7). Basis = plane waves at exactly the tidal
forcing frequency, **purely persistent in time** (fully phase-locked/coherent over the
25-yr record), spatially localized by a Hamming window spanning 3 wavelengths, 12
propagation directions, sine/cosine pairs per direction; wavelengths from the
dispersion relation `ω² = k²c² + f²` (Eq. 11, p.6) with phase speed `c_p = ω c/√(ω² −
f²)` (Eq. 12) and c from the Chelton et al. 1998 first-baroclinic climatology; mode-2
uses c/2 (§3.2.2, p.6, Fig. 3b/d). Q for IT elements is constant ("equi-probability",
p.6). The headline scientific result: simultaneous mesoscale+IT estimation avoids the
two-way aliasing that separate or sequential estimation suffers (1-D proof §2.2,
Figs. 1–2; real-data ablations Hawaii/Gulf Stream §3.3.1, Figs. 8–9), and the IT
solution slightly beats Zaron 2019 HRET on M2 crossover variance reduction globally
(Table 1, p.10: −0.16 cm² global vs Zaron). Relevance to core: this paper is where
the **global tiling machinery** (§2.8 above) and the AltiKa-spectrum Q database are
documented; its mesoscale solution itself is explicitly not validated (§3.3, p.7).

### 4.3 Equatorial waves (B2023) — out of scope

Two SSH-only components confined to 10°S–10°N (current blocks zeroed; B2023 App. A2
pp.17–18): tropical instability waves (TIW) and Poincaré (inertia-gravity) waves.
Same wavelet machinery but with a **propagating carrier** `cos(ωt − kx)` — propagation
encoded in the basis, unlike the mesoscale component (Eqs. A19–A20, p.19). Frequencies
from prescribed dispersion relations (Eq. 4/A21): Poincaré `ω = √(k²c² + βc(2n+1))`,
c = ±2.8 m/s, meridional mode n = 1,2,3…; TIW `ω = ck`, c = −0.5 m/s westward (Eq. 5,
p.5; App. A2.2, p.19). Taper half-widths: Poincaré 1000 km zonal / 300 km meridional /
5 d; TIW 500 km / 300 km / 20 d (§2.2 p.5; App. A2.2 p.19). Q values: NS. Motivation:
DUACS filters periods <10 d, discarding mappable 4–10 d basin-scale waves (§2.2 p.4).
Impact: equatorial-band mapping error reduced ~3% on average, >10–20% locally
(Tables 6, 8; §4.2.2–4.2.3, pp.9–11); resolves 4/5/7-d Poincaré spectral peaks matching
GLORYS12v1 (Fig. 7, p.9).

### 4.4 Drifter ingestion + Arctic leads (B2023) — out of scope

**Drifters:** AOML SVP drifters, 6-h positions, drogued at 15 m (CMEMS INS-TAC copy
with Rio 2012 wind-slippage correction for undrogued buoys) (§2.1.3, pp.3–4). The
ingested quantity is a *geostrophic velocity anomaly*: total drifter velocity minus
Ekman (ERA5-forced model), Stokes (undrogued only), inertial/tidal/HF filtering, and
MDT (CNES-CLS18) — Eqs. 2–3, p.3. These enter the same inversion through the
geostrophy component's analytic current blocks (Eq. A18, p.19 — the U2021 Eq. 20
pattern): the extended obs vector is `y = (h°ᵀ, u_r°ᵀ)ᵀ` (Eq. A11, p.18). Assessed
run ingests 80% of trajectories, withholds 20%, excludes ±10° band (§3.1, p.6).
Impact "moderate": ~1.5% SSH error-variance reduction in high-variability regions
(65–500 km band), a few % on currents (§4.2.2, p.10; Table 7). Drifter obs-error: NS.
**Arctic leads:** experimental along-track SLA from lead echoes (AltiKa/S3A LRM-
adaptive/TFMRA-retracked, CryoSat-2 to 88°N), modified correction stack, ~8 cm
per-mission continuity bias, 20 Hz (§2.1.2, pp.2–3, Table 2) — enables gap-free Arctic
maps (Fig. 5, p.8), flagged by the paper itself as not yet independently validated
(§6, p.13).

---

## 5. MIOST output vs sverdrup's capability taxonomy

sverdrup contract (read from `core/types.py::UncertaintyCapability` via
`core/method.py`, and `core/distribution.py`): capability ladder `POINT →
MARGINAL_VARIANCE → COVARIANCE → SAMPLES`; a `Method` declares `native_capability` and
`solve()` returns a `PredictiveDistribution` exposing `marginal_variance()`,
`covariance(a,b)`, `sample(m,seed)`.

**DOCUMENTED: MIOST is POINT-only as shipped, in all three papers.**

- U2021: the general OI formalism includes the analysis-error covariance `B^a = (I −
  KH)B` "…can be used to characterize the uncertainty of the solution" (Eq. 4, p.3),
  and the *basic* 2×2 current LS uses `B^a = (HᵀR⁻¹H)⁻¹` for schematic error ellipses
  (Eq. 7, Fig. 1, p.4) — but for the reduced-space multiscale mapping **no posterior
  variance, error map, or ensemble is ever computed or shown**; the distributed data
  are "reference fields, synthetic observations and gridded analysis" only (Data
  Availability, p.17).
- U2022: **explicitly names uncertainties as not-done future work**: "The computation
  of uncertainties could be an interesting next step. Indeed, it would be possible to
  provide estimations of errors, with respect to the covariance model prescribed
  through the mode decompositions … (first given in the parameter space, but then
  projectable in physical space)" (Conclusions, pp.11–12).
- B2023: the shipped product contains **six variables: sla, adt, ugosa, vgosa, ugos,
  vgos** (§5 p.13; Fig. 15 p.16) — no error/variance variable. (DUACS ships `err_sla`;
  B2023 does not discuss an equivalent for MIOST.)

So on the papers' own record: **no MARGINAL_VARIANCE, no COVARIANCE, no SAMPLES —
mean-only.** Under sverdrup's taxonomy the documented MIOST is `native_capability =
POINT`. That honestly reframes MIOST-as-documented as a baseline/comparison target
rather than a Method peer on the uncertainty axis; whether to implement it that way,
or to expose the latent posterior (below), is the owner's later design decision — not
made here.

**INFERENCE (mine, one paragraph, clearly marked).** The estimator is exactly a
linear-Gaussian MAP in a finite coefficient space, so a full Gaussian posterior
*exists in principle*: `η | y ~ N(η^a, P)` with `P = (Gᵀ R⁻¹ G + Q⁻¹)⁻¹`, and any
field query is a linear functional of η (`x = Γη`), giving posterior field covariance
`Γ_s P Γ_sᵀ` between arbitrary space–time points, marginal variances from its
diagonal, and exact samples via `η^a + P^{1/2}ξ`. U2022's conclusions independently
confirm the structure ("first given in the parameter space, but then projectable in
physical space"). In principle this spans the entire sverdrup ladder up to SAMPLES.
The practical obstacles (P is the inverse of the implicitly defined A that is only
ever touched matrix-free; ~10⁵–10⁹ coefficients; per-tile posteriors would face
cross-seam questions this project already knows intimately) are real but belong to
the design session, not this brief. Nothing here is documented MIOST behavior.

---

## 6. Relation to classical OI — ANALYSIS (marked; not a paper claim except where cited)

The papers themselves state the pieces: Eq. 2 of U2021 (p.2) "is known as Optimal
Interpolation"; the reduced-space solve is that same equation after `B = ΓQΓᵀ`
(U2021 Eq. 12/U2022 Eq. 10/B2023 Eq. A10) and a Sherman–Morrison–Woodbury switch to
information form (U2021 Eq. 3; U2022 Eq. 13 "Sherman–Woodbury transformation"; B2023
Eq. A7). The wavelet ensemble is designed "to approximate the standard covariance
models used in altimetry mapping" (U2021 §2.3.2.1, p.6), and its representer
reproduces the Le Traon-style covariance with negative lobe (U2022 Fig. 4, p.5–6).

ANALYSIS (mine): therefore **MIOST's core is a reduced-rank formulation of exactly the
linear-Gaussian problem sverdrup's OI solves**, with three substitutions: (1) the
kernel-defined prior covariance is replaced by the low-rank factorization `B = Γ Q Γᵀ`
implied by the wavelet dictionary and its diagonal variances — covariance is *chosen
implicitly* by basis design rather than *evaluated* from a closed-form kernel; (2) the
obs-space solve (invert `HBHᵀ + R`, size = #obs — sverdrup OI's path, and DUACS's per
B2023 App. A1) is replaced by the coefficient-space normal equations (invert `GᵀR⁻¹G +
Q⁻¹`, size = #elements) via matrix-free PCG — advantageous precisely when #obs ≫
#coefficients over long windows; (3) one global-in-window solve with multiple additive
covariance components replaces DUACS-style local moving-window inversions with a
single-scale kernel (B2023 §2.2, p.4 states this contrast). Differences that are
substantive, not cosmetic: MIOST's mesoscale prior has no propagation term (DUACS's
does — B2023 Eqs. A3–A4), its covariance is only approximately stationary/isotropic
(pavement + spectrum-binned Q), and its effective kernel is compactly supported by
construction. Positioning consequence (owner's call later): as an estimator class,
MIOST is "OI with a different prior parameterization and solver", so a sverdrup MIOST
could legitimately be a Method peer of OI on the POINT axis even if shipped
capability stays POINT; §5 governs the uncertainty axis.

---

## 7. Validation anchor for a future sverdrup MIOST

What the papers report (none of it is a 2021a-harness metric):

- U2021: OSSE spectral score `100·(1−r)` vs NATL60 truth; geostrophic effective
  resolving ≈110 km (altimetry-only, basic mapping) (§4.2, p.15, Fig. 12). No μ-style
  RMSE score; the 2021a challenge postdates the paper.
- U2022: internal-tide variance reduction only (Table 1, p.10); "The mesoscale
  solution … is not analyzed in this paper" (§3.3, p.7).
- B2023: closest to the harness. Independent-AltiKa error variance (Eq. 6–7, p.6) —
  MIOST allsat-1 (geostrophy-only, altimetry-only) beats DUACS allsat-1 by −5.8 to
  −10.2% (all scales) and −2.6 to −9.9% (65–500 km) outside Arctic/Equator (Table 4,
  p.10); effective resolution per Ballarotta et al. 2019 SNR(λ_s)=2 (Eqs. 8–9, p.7) —
  **the same metric family as the 2021a challenge's λx** — MIOST 5–10% finer than
  DUACS in high-variability regions (Fig. 14, §4.2.3, p.12). The paper never mentions
  the 2021a data challenge by name.

**The acceptance reference for any sverdrup MIOST** is the vendored leaderboard row
(`vendor/2021a_SSH_mapping_OSE/README.md`, line 31):

> MIOST | μ = 0.89 | σ = 0.08 | λx = 139 km | "Multiscale mapping" |
> `example_eval_miost.ipynb`

evaluated by the same harness sverdrup's OI (reproduced BASELINE 0.853/0.090/140.9)
and GMRF are scored on. GAP, flagged: **which MIOST configuration produced that row is
not documented in the three papers** (no paper describes the 2021a submission; the
challenge run is altimetry-only over the 2017 Gulf Stream box, so the minimal core of
this brief is the right family, but its exact scales/Q/R are unknown). The
`example_eval_miost.ipynb` notebook in the vendored challenge repo evaluates the
challenge's distributed MIOST maps; it does not document the generating configuration
either (it is an evaluation notebook).

**Honesty consequence (owner-reviewed 2026-07-02):** given the gaps register (§8) and
the absence of any public MIOST implementation, a sverdrup MIOST would be
**family-faithful and tuned-in-framework, NOT a reproduction of the CLS
configuration** — reproduction is impossible from the public record. The leaderboard
row is therefore an *aspirational* acceptance anchor (target, not hard gate — the
Stage-A lesson about the DUACS bar applies).

---

## 8. Gaps register — load-bearing unknowns, flagged not filled

Everything a faithful reimplementation needs that is **in none of the three papers**:

1. **Element spacing** (space, time, wavenumber) as a fraction of scale — controls
   basis size and covariance fidelity. All papers: "inversely proportional to the
   wavelet extensions", no number.
2. **Direction count** for the mesoscale plane-wave carrier.
3. **Q calibration**: spectrum functional form/binning, geographic parameterization,
   and the PSD→element-variance normalization (incl. sine/cosine pair split).
4. **R values** for real altimetry data (per-mission or global).
5. **Preconditioner** and CG convergence tolerance.
6. **Temporal pavement spacing** and treatment of window edges in time.
7. **L_t for the operational/global runs** (only U2021's regional "≈10 d" is numeric).
8. **Per-tile problem sizes** and any per-tile Q/R adjustments.
9. **The exact 2021a-challenge MIOST configuration** (§7).
10. Whether any **normalization makes the coefficient prior identity** (papers keep
    Q explicit; U2022's orthogonality claim is asserted, not constructed).

**Gap-closure status (owner-verified 2026-07-02):** **no public MIOST implementation
exists** as of this date. All three papers' availability statements distribute
PRODUCTS only (U2021: Zenodo 4506248 = reference fields / synthetic obs / gridded
analysis; U2022/B2023: AVISO DOIs for the IT solution and the gridded product).
GitHub search: negative on the method name (27 unrelated hits), on the author name
(0 hits), and across the ocean-data-challenges org (challenge/eval repos only).
Closure routes are therefore: **(a)** the authors / the AVISO+ product handbook
(offline, outside this sandbox); **(b)** treat gaps 1–5 as a tunable
`parameter_space` closed in-framework by the Phase-5 autotune loop, with the vendored
MIOST leaderboard row as the ASPIRATIONAL acceptance anchor (target, not hard gate —
see §7). Route choice is the OWNER'S, at design time.

---

## 9. Errata observed in the papers (useful when reviewing this brief against the PDFs)

- U2021 Eq. 25 (p.9): third line labeled `Γ_{3,u}` twice; second occurrence is
  plainly `Γ_{3,v}` (verified against typeset PDF).
- U2022 §3.2.3 (p.7): "Sherman–Woodbury transformation of Eq. (10)" — logically
  should reference Eq. (8). Same section: "matrix invisibility" for "invertibility";
  "half the tidal frequency" for "period". §1→§2 cross-reference off by one section.
- U2022 §3.2.2 (p.6): "phase speed … divided by 0" — typo for 2 (mode-2).
- U2022 §3.3.2: independent-period end date inconsistent between text (Dec 2018) and
  Fig. 10 caption (Dec 2019).
- B2023 Eq. A2 (p.17): prints `(HBHᵀ − R)⁻¹`; standard OI has `+R` — sign typo.
- B2023 Eq. A17 (p.18): taper prints `cos(π/2 δy)` twice; third factor is plainly δt
  (cf. U2021 Eq. 19).

---

## 10. Provenance of this brief

Produced 2026-07-02 from the three PDFs in `docs/papers/` only (sandbox blocks
external fetches; nothing filled from memory). Extraction: three parallel subagents,
one per PDF, using pypdf full-text extraction (the container lacks poppler, so no
native PDF rendering); for U2021, equation regions were additionally rendered to
images via pymupdf and all transcribed signs verified against the typeset equations.
Load-bearing quotes were independently re-verified against the raw extracted text
("between 80 km and 800 km", "1.5 the wavelength", "preconditioned conjugate
gradient", "15 by 15° tiles" + 2° overlap + linear blending, "typically 100
iterations", "2 TB / 200 threads", the U2022 uncertainty-future-work sentence, the
AltiKa-spectrum→Q sentence, "between 80 and 900 km", "six variables: sla, adt, …").
Working artifacts (alongside this brief): `ubelmann2021.extraction.md`,
`ubelmann2022.extraction.md`, `ballarotta2023.extraction.md` (structured per-paper
extractions with full citation detail, incl. full transcriptions of U2022 Table 1 and
B2023 Tables 1–9) and `*.pdftext.txt` (raw pypdf dumps for grep-verification).

**The working artifacts and the PDFs are INTENTIONALLY uncommitted** (gitignored,
2026-07-02): this is a public repo, the extraction files and raw dumps are full-text
transcriptions of the papers (republishing), and U2021's license is unverified. Do
NOT "fix" this by committing them. The brief itself is the only versioned account.

**Review outcome (owner review, 2026-07-02) — accepted at every reachable tier:**
brief↔extractions: all probed load-bearing quotes present and faithful (80–800 vs
80–900, 1.5× wavelength, tiling quote, 100 iterations, U2022 future-work sentence,
B2023 six-variables); the two key negatives (no numeric spacing; no R values) are
independently flagged inside the extractions; "MIOST absent from U2021" self-verified
by the extractor; no drift found. Brief↔repo: `UncertaintyCapability` at
`core/types.py:15`, `native_capability` at `core/method.py:20`,
`PredictiveDistribution` methods verified exactly as stated. Brief↔leaderboard: MIOST
row (μ=0.89, σ=0.08, λx=139, README line 31) verified. Remaining tier: the owner's
own extraction↔PDF spot-check (in progress, separate).
