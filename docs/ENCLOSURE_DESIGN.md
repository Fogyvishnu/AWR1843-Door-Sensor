# Enclosure & Radome Mechanical Engineering Guide

## TI AWR1843BOOST 77 GHz mmWave Door Sensor
**Document Version:** 1.3.0  
**Classification:** Mechanical & RF Integration Guide

---

## 1. 77 GHz mmWave Radome Physics

At millimeter-wave frequencies (76–81 GHz), electromagnetic waves possess a free-space wavelength of:

```math
\lambda_0 = \frac{c}{f_0} = \frac{3 \times 10^8\text{ m/s}}{77 \times 10^9\text{ Hz}} \approx 3.896\text{ mm}
```

When transmitting through a non-metallic enclosure (radome), reflections occur at both the front and back plastic interfaces. Improper wall thickness or partial infill creates destructive phase interference, introducing severe transmission attenuation (up to 15 dB) and strong stationary ghost reflections that blind the radar receiver.

### Half-Wavelength Matching Principle
To achieve maximum electromagnetic transparency ($>98\%$ transmission efficiency), the radome window directly in front of the AWR1843 patch antennas must satisfy the **half-wavelength impedance matching condition**:

```math
d = \frac{m \cdot \lambda_0}{2 \sqrt{\epsilon_r - \sin^2(\theta)}}
```

where:
- $m \in \{1, 2, 3, \dots\}$ is the harmonic mode (mode $m=1$ provides lowest dielectric absorption loss)
- $\epsilon_r$ is the relative dielectric constant of the plastic
- $\theta$ is the incidence angle ($\theta \approx 0^\circ$ for normal boresight radiation)

For normal incidence ($\theta = 0^\circ$):

```math
d = \frac{c}{2 f_0 \sqrt{\epsilon_r}} = \frac{1.948\text{ mm}}{\sqrt{\epsilon_r}}
```

---

## 2. Material Selection & Optimal Wall Thickness

| Material | Dielectric Constant ($\epsilon_r$ @ 77GHz) | Loss Tangent ($\tan\delta$) | Recommended Wall Thickness ($m=1$) | Suitability Rating |
|---|---|---|---|---|
| **Polycarbonate (PC)** | $2.85$ | $0.006$ | **$1.15\text{ mm}$** | ⭐⭐⭐⭐⭐ (Best impact & thermal resistance) |
| **ABS** | $2.65$ | $0.008$ | **$1.20\text{ mm}$** | ⭐⭐⭐⭐⭐ (Excellent general-purpose 3D print) |
| **PLA** | $2.95$ | $0.015$ | **$1.13\text{ mm}$** | ⭐⭐⭐⭐☆ (Good prototype, low heat tolerance) |
| **PETG** | $2.80$ | $0.012$ | **$1.16\text{ mm}$** | ⭐⭐⭐⭐☆ (Good UV & moisture resistance) |
| **PTFE (Teflon)** | $2.05$ | $0.0004$ | **$1.36\text{ mm}$** | ⭐⭐⭐⭐⭐ (Lowest RF loss, machining required) |

> [!CRITICAL]
> **3D Printing Infill Requirement:**  
> The antenna window area on the front face of the enclosure MUST be printed with **100% solid infill** (concentric or rectilinear). Printing with standard 15%–30% grid infill introduces internal air cavities that act as random diffraction gratings, causing severe beam distortion and false ghost points!

---

## 3. Physical Spacing & Antenna Clearance

- **Air Gap ($s$)**: Maintain a minimum air gap of **$4.0\text{ mm}$ to $8.0\text{ mm}$** between the printed circuit board antenna array and the inner surface of the radome wall.
  - An air gap smaller than $2\text{ mm}$ disrupts the near-field reactive impedance of the microstrip patch antennas.
- **Metal Proximity**: All metal screws, standoffs, and mounting hardware must maintain a clearance of at least **$25.0\text{ mm}$** from the active antenna keep-out zone on the top-left section of the AWR1843BOOST PCB.

```
       +---------------------------------------------+
       |               Radome Front Face             |
       |  =================== [d = 1.15 mm] =======  |
       |             ^                               |
       |             |  Air Gap s = 5.0 mm           |
       |             v                               |
       |      [Antenna Array]                        |
       |      +-------------+                        |
       |      | AWR1843 PCB |                        |
       |      +-------------+                        |
       |             |                               |
       |             v  Thermal Venting Bottom       |
       |         ===   ===   ===                     |
       +---------------------------------------------+
```

---

## 4. Thermal Dissipation & Venting

During continuous active chirping, the AWR1843 RF transceiver and C674x DSP dissipate approximately **$1.6\text{ W} - 2.1\text{ W}$** of thermal energy. In unventilated enclosures, internal temperatures can exceed $75^\circ\text{C}$, triggering the sensor's thermal shutdown protection.

### Ventilation Guidelines:
1. Provide convection slots on the **bottom and rear surfaces** of the enclosure.
2. Never place ventilation holes directly on the front radome window facing the antenna.
3. For harsh outdoor or industrial environments requiring IP54 / IP65 water ingress protection, utilize a sealed aluminum backplate with thermal interface pad (TIM) coupled to the rear ground plane of the PCB to conduct heat out without air vents.

---

## 5. Mounting Bracket Configurations

### Configuration 1: Header Mount (Top-Down 45° Pitch)
- **Position**: Mounted on the upper door frame (header), angled downwards at $30^\circ - 45^\circ$.
- **Advantages**:
  - Maximum field of view across the entire door arc.
  - Immune to floor clutter or sweeping broom interference.
  - Ideal for swinging single and double doors.

### Configuration 2: Lateral Wall Mount (Boresight Level)
- **Position**: Mounted on the latch-side wall at mid-height ($1.0\text{ m} - 1.2\text{ m}$ from floor), facing perpendicular to the closed door surface.
- **Advantages**:
  - Direct specular reflection from door face, yielding highest SNR ($>25\text{ dB}$).
  - Simplest installation for sliding pocket doors and standard residential doors.
