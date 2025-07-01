# Literature Survey

## Adaptive ECC Switching

Adaptive switching selects an error correcting code on the fly based on the
observed fault rate and application needs. Many designs keep a lightweight
SEC‑DED code active during normal operation to minimize latency. When the
decoder begins to report frequent failures the controller reconfigures the
memory to use a stronger BCH or product code. This approach trades additional
energy and storage only when higher reliability is required, allowing the
system to adapt over the lifetime of the device.

## Sustainability Metrics

Sustainability is measured through the total energy consumed per decode and the
estimated carbon footprint of that energy. The simulators count XOR and AND
operations and convert them into joules using the constants from the energy
model. To approximate environmental impact, the energy figure is multiplied by
the carbon intensity of the deployment region. Such metrics enable apples to
apples comparisons between ECC schemes when optimizing for both correctness and
ecological cost.

## Relevant Papers

- **Hamming, R.W. (1950)** – Introduced error detecting and correcting codes,
  establishing the classic SEC‑DED framework.
- **Lin and Costello, *Error Control Coding*** – Comprehensive reference on
  BCH and Reed‑Solomon techniques used for multi‑bit protection.
- **Sampson et al. (2013)** – Presents cross‑layer reliability management
  where adaptive ECC selection balances energy against detected fault rates.
- **Shao et al. (2020)** – Discusses sustainability considerations for memory
  systems and proposes metrics to evaluate ECC overhead in terms of carbon
  emissions.
