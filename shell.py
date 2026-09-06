#!/usr/bin/env python3
"""
LQE Shell -- Interactive Quantum Circuit Builder

Type commands. See results immediately. No coding required.

Examples:
  > new 2          (create 2-qubit simulator)
  > h 0            (apply H to qubit 0)
  > cnot 0 1       (apply CNOT)
  > state           (see the quantum state)
  > probs           (see measurement probabilities)
  > measure 0      (measure qubit 0)
  > new 3          (start over with 3 qubits)
  > help           (list all commands)
  > quit           (exit)
"""

import sys, numpy as np
sys.path.insert(0, ".")

from legitimate_quantum_engine import StatevectorSim

class QuantumShell:
    def __init__(self):
        self.sim = None
        self.n = 0
        self.history = []

    def banner(self):
        print()
        print("=" * 50)
        print("  LEGITIMATE QUANTUM ENGINE -- Interactive Shell")
        print("=" * 50)
        print()
        print("Type 'help' for commands, 'new 2' to start.")
        print()

    def prompt(self):
        if self.sim is None:
            return "> "
        return f"[{self.n}q] > "

    def do_new(self, args):
        """new N -- Create N-qubit simulator."""
        if not args:
            print("Usage: new <number_of_qubits>")
            return
        try:
            n = int(args[0])
            if n < 1 or n > 20:
                print("Qubits must be 1-20 (memory limit on phone)")
                return
            self.n = n
            self.sim = StatevectorSim(n)
            self.history = []
            print(f"Created {n}-qubit simulator. State: |{'0'*n}>")
        except ValueError:
            print("Usage: new <number_of_qubits>")

    def do_h(self, args):
        """h Q -- Apply Hadamard to qubit Q."""
        self._apply_gate("H", args)

    def do_x(self, args):
        """x Q -- Apply X (NOT) to qubit Q."""
        self._apply_gate("X", args)

    def do_y(self, args):
        """y Q -- Apply Y to qubit Q."""
        self._apply_gate("Y", args)

    def do_z(self, args):
        """z Q -- Apply Z to qubit Q."""
        self._apply_gate("Z", args)

    def do_rx(self, args):
        """rx ANGLE Q -- Apply RX(angle) to qubit Q. Angle in radians."""
        if len(args) != 2:
            print("Usage: rx <angle> <qubit>")
            return
        try:
            angle = float(args[0])
            q = int(args[1])
            self._check_sim()
            self.sim.apply("RX", angle, q)
            self.history.append(f"RX({angle:.3f}) on {q}")
            print(f"Applied RX({angle:.3f}) to qubit {q}")
        except (ValueError, IndexError) as e:
            print(f"Error: {e}")

    def do_ry(self, args):
        """ry ANGLE Q -- Apply RY(angle) to qubit Q."""
        if len(args) != 2:
            print("Usage: ry <angle> <qubit>")
            return
        try:
            angle = float(args[0])
            q = int(args[1])
            self._check_sim()
            self.sim.apply("RY", angle, q)
            self.history.append(f"RY({angle:.3f}) on {q}")
            print(f"Applied RY({angle:.3f}) to qubit {q}")
        except (ValueError, IndexError) as e:
            print(f"Error: {e}")

    def do_rz(self, args):
        """rz ANGLE Q -- Apply RZ(angle) to qubit Q."""
        if len(args) != 2:
            print("Usage: rz <angle> <qubit>")
            return
        try:
            angle = float(args[0])
            q = int(args[1])
            self._check_sim()
            self.sim.apply("RZ", angle, q)
            self.history.append(f"RZ({angle:.3f}) on {q}")
            print(f"Applied RZ({angle:.3f}) to qubit {q}")
        except (ValueError, IndexError) as e:
            print(f"Error: {e}")

    def do_cnot(self, args):
        """cnot C T -- Apply CNOT with control C, target T."""
        if len(args) != 2:
            print("Usage: cnot <control> <target>")
            return
        try:
            c, t = int(args[0]), int(args[1])
            self._check_sim()
            self.sim.apply("CNOT", c, t)
            self.history.append(f"CNOT({c},{t})")
            print(f"Applied CNOT: control={c}, target={t}")
        except (ValueError, IndexError) as e:
            print(f"Error: {e}")

    def do_swap(self, args):
        """swap A B -- Swap qubits A and B."""
        if len(args) != 2:
            print("Usage: swap <qubit1> <qubit2>")
            return
        try:
            a, b = int(args[0]), int(args[1])
            self._check_sim()
            self.sim.apply("SWAP", a, b)
            self.history.append(f"SWAP({a},{b})")
            print(f"Applied SWAP: {a} <-> {b}")
        except (ValueError, IndexError) as e:
            print(f"Error: {e}")

    def do_state(self, args):
        """state -- Show the current quantum state vector."""
        self._check_sim()
        print()
        print("Quantum State:")
        print("-" * 40)
        dim = 2 ** self.n
        for i in range(dim):
            amp = self.sim.state[i]
            if abs(amp) > 1e-10:
                label = f"|{i:0{self.n}b}>"
                if abs(amp.imag) > 1e-10:
                    print(f"  {label}: {amp.real:+.4f} {amp.imag:+.4f}i")
                else:
                    print(f"  {label}: {amp.real:+.4f}")
        print()

    def do_probs(self, args):
        """probs -- Show measurement probabilities."""
        self._check_sim()
        probs = self.sim.probabilities()
        print()
        print("Measurement Probabilities:")
        print("-" * 40)
        dim = 2 ** self.n
        for i in range(dim):
            p = probs[i]
            if p > 1e-10:
                label = f"|{i:0{self.n}b}>"
                bar = "█" * int(p * 30)
                print(f"  {label}: {p:.4f} {bar}")
        print()

    def do_measure(self, args):
        """measure Q -- Measure qubit Q (0 to n-1)."""
        if not args:
            print("Usage: measure <qubit>")
            return
        try:
            q = int(args[0])
            self._check_sim()
            result = self.sim.measure(q)
            print(f"Measured qubit {q}: {result}")
            print("(State has collapsed. Use 'state' to see new state.)")
        except (ValueError, IndexError) as e:
            print(f"Error: {e}")

    def do_measure_all(self, args):
        """measure_all -- Measure all qubits at once."""
        self._check_sim()
        result = self.sim.measure_all()
        print(f"Measured all qubits: {result} (binary: {result:0{self.n}b})")

    def do_history(self, args):
        """history -- Show gates applied so far."""
        if not self.history:
            print("No gates applied yet.")
            return
        print()
        print("Circuit History:")
        print("-" * 40)
        for i, gate in enumerate(self.history, 1):
            print(f"  {i}. {gate}")
        print()

    def do_bell(self, args):
        """bell -- Create Bell state on qubits 0 and 1."""
        if self.sim is None or self.n < 2:
            print("Need at least 2 qubits. Type: new 2")
            return
        self.sim = StatevectorSim(self.n)
        self.history = []
        self.sim.apply("H", 0)
        self.sim.apply("CNOT", 0, 1)
        self.history = ["H on 0", "CNOT(0,1)"]
        print("Created Bell state: (|00> + |11>)/sqrt(2)")
        self.do_state([])

    def do_ghz(self, args):
        """ghz -- Create GHZ state on all qubits."""
        if self.sim is None:
            print("Create a simulator first. Type: new <N>")
            return
        self.sim = StatevectorSim(self.n)
        self.history = []
        self.sim.apply("H", 0)
        for i in range(self.n - 1):
            self.sim.apply("CNOT", i, i + 1)
        self.history = ["H on 0"] + [f"CNOT({i},{i+1})" for i in range(self.n - 1)]
        print(f"Created GHZ state on {self.n} qubits")
        self.do_state([])

    def do_random(self, args):
        """random N -- Generate N quantum random bits."""
        n = int(args[0]) if args else 8
        bits = ""
        for _ in range(n):
            s = StatevectorSim(1)
            s.apply("H", 0)
            bits += str(s.measure(0))
        print(f"Quantum random bits: {bits}")
        print(f"As integer: {int(bits, 2) if bits else 0}")

    def do_vqe(self, args):
        """vqe -- Run VQE on 4-qubit TFI model."""
        from legitimate_quantum_engine import VQE, tfi_hamiltonian
        print("Running VQE on 4-qubit transverse-field Ising model...")
        H = tfi_hamiltonian(4)
        vqe = VQE(4, H, num_layers=2, max_iterations=200)
        result = vqe.solve(verbose=False)
        exact = -3.46
        print(f"Energy found: {result['energy']:.4f}")
        print(f"Exact answer: {exact:.2f}")
        print(f"Error: {abs(result['energy'] - exact):.4f}")

    def do_help(self, args):
        """help -- Show all commands."""
        print()
        print("COMMANDS:")
        print("-" * 50)
        print("  new N          Create N-qubit simulator (1-20)")
        print("  h Q            Hadamard on qubit Q")
        print("  x Q            X (NOT) on qubit Q")
        print("  y Q            Y on qubit Q")
        print("  z Q            Z on qubit Q")
        print("  rx ANGLE Q     RX rotation on qubit Q")
        print("  ry ANGLE Q     RY rotation on qubit Q")
        print("  rz ANGLE Q     RZ rotation on qubit Q")
        print("  cnot C T       CNOT: control C, target T")
        print("  swap A B       Swap qubits A and B")
        print()
        print("  state          Show quantum state")
        print("  probs          Show measurement probabilities")
        print("  measure Q      Measure qubit Q")
        print("  measure_all    Measure all qubits")
        print("  history        Show gates applied")
        print()
        print("  bell           Create Bell state (needs 2+ qubits)")
        print("  ghz            Create GHZ state (needs 1+ qubits)")
        print("  random N       Generate N quantum random bits")
        print("  vqe            Run VQE demo")
        print()
        print("  help           Show this help")
        print("  quit           Exit")
        print()
        print("EXAMPLES:")
        print("  > new 2")
        print("  > h 0")
        print("  > cnot 0 1")
        print("  > state")
        print("  > probs")
        print()

    def do_quit(self, args):
        """quit -- Exit the shell."""
        print("Goodbye.")
        sys.exit(0)

    def _apply_gate(self, name, args):
        if len(args) != 1:
            print(f"Usage: {name.lower()} <qubit>")
            return
        try:
            q = int(args[0])
            self._check_sim()
            self.sim.apply(name, q)
            self.history.append(f"{name} on {q}")
            print(f"Applied {name} to qubit {q}")
        except (ValueError, IndexError) as e:
            print(f"Error: {e}")

    def _check_sim(self):
        if self.sim is None:
            raise IndexError("No simulator. Type: new <number_of_qubits>")

    def run(self):
        self.banner()
        while True:
            try:
                line = input(self.prompt()).strip()
                if not line:
                    continue
                parts = line.split()
                cmd = parts[0].lower()
                args = parts[1:]

                method = getattr(self, f"do_{cmd}", None)
                if method:
                    try:
                        method(args)
                    except IndexError as e:
                        print(f"Error: {e}")
                else:
                    print(f"Unknown command: '{cmd}'. Type 'help' for list.")

            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print()
                break

def main():
    """Entry point for lqe-shell console script."""
    shell = QuantumShell()
    shell.run()


if __name__ == "__main__":
    main()
