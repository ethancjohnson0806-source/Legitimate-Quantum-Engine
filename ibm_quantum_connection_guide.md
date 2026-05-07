# Connecting Your LegitimateQuantumEngine to IBM Quantum Hardware

This guide will walk you through the process of setting up your IBM Quantum account and connecting it to your `LegitimateQuantumEngineV3` to run circuits on real quantum hardware or high-fidelity simulators.

## 1. Create an IBM Quantum Account

If you don't already have one, you'll need to create a free IBM Quantum account. This will give you access to their quantum computers and simulators.

1.  Navigate to the [IBM Quantum Experience website](https://quantum.ibm.com/).
2.  Click on "Register" or "Sign up" and follow the prompts to create your account. You can often use a Google or GitHub account for quick registration.

## 2. Obtain Your IBM Quantum API Token

Your API token is a unique key that authenticates your access to IBM Quantum services.

1.  Once logged into the [IBM Quantum Experience](https://quantum.ibm.com/), click on your profile icon (usually in the top right corner).
2.  Select "Account settings" or "My account."
3.  On your account page, you should find a section labeled "API token" or "Access tokens." Copy this token. **Keep this token secure and do not share it publicly.**

## 3. Save Your API Token Locally (Recommended)

Qiskit provides a convenient way to save your API token locally so you don't have to pass it every time you initialize the engine. This is the recommended approach for security and convenience.

1.  Open a terminal or command prompt.
2.  Run the following Python code. Replace `YOUR_API_TOKEN_HERE` with the token you copied from the IBM Quantum Experience website:

    ```python
    from qiskit_ibm_runtime import QiskitRuntimeService

    # Replace 'YOUR_API_TOKEN_HERE' with your actual IBM Quantum API token
    QiskitRuntimeService.save_account(channel="ibm_quantum", token="YOUR_API_TOKEN_HERE")
    print("IBM Quantum account saved successfully!")
    ```

    After running this, your token will be securely stored on your system, and Qiskit will automatically load it in the future.

## 4. Initialize Your `LegitimateQuantumEngineV3` for Hardware Access

Now, you can modify your `quantum_engine_v3_hardware.py` script to utilize the IBM Quantum services. If you have saved your account as described in Step 3, you can initialize the engine without explicitly passing the token:

```python
# In your quantum_engine_v3_hardware.py script or a new script:

from quantum_engine_v3_hardware import LegitimateQuantumEngineV3

# Initialize the engine. If you saved your account, no token is needed here.
# Otherwise, you can pass it directly: engine = LegitimateQuantumEngineV3(ibm_token="YOUR_API_TOKEN_HERE")
engine = LegitimateQuantumEngineV3(num_qubits=5) # Use a small number of qubits for free tier

# Run the evolution with hardware access enabled
# You can specify a backend name, e.g., "ibm_brisbane" or "ibmq_qasm_simulator"
# For initial testing, 'ibmq_qasm_simulator' is recommended as it's a high-fidelity simulator.
# Check available backends on the IBM Quantum Experience website.

history = engine.evolve(iterations=5, use_hardware=True, backend_name="ibmq_qasm_simulator")

print("Hardware-enabled evolution complete!")
```

### **Important Notes:**

*   **Backend Selection**: IBM Quantum offers various real quantum devices and simulators. You can view the available backends and their status on the [IBM Quantum Experience](https://quantum.ibm.com/services/resources) website. For initial testing, `ibmq_qasm_simulator` is highly recommended as it provides quick results without queue times.
*   **Qubit Limits**: Free tier accounts on IBM Quantum typically have limitations on the number of qubits and execution time. Start with small circuits (e.g., `num_qubits=5` or `6`) to stay within these limits.
*   **Queue Times**: Real quantum hardware can have significant queue times. Be patient if you choose to run on a physical device.
*   **Cost**: While there is a free tier, be mindful of usage if you explore advanced features or larger devices, as some services may incur costs.

By following these steps, you will be able to leverage the power of IBM Quantum's cloud infrastructure to run your `LegitimateQuantumEngineV3` on actual quantum computing resources.
