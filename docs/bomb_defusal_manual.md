# BOMB DEFUSAL MANUAL

**CLASSIFIED — FIELD OPERATIONS USE ONLY**

This manual is for the expert team communicating with the defuser over radio. The defuser can see the bomb but NOT this manual. The expert team has this manual but CANNOT see the bomb. Work together.

The bomb has a **serial number** (shown on screen, e.g. `AB1234`), a **countdown timer**, and several **modules**. All modules must be solved before the timer expires. Three strikes and the bomb detonates.

---

## MODULE 1: WIRES

The defuser will see 3–6 colored wires. They must describe the **number of wires** and **each wire's color in order** (top to bottom). Then use the rules below to determine which wire to cut.

### 3 Wires
- If there are no RED wires, cut the **2nd wire**.
- Otherwise, if the last wire is WHITE, cut the **last wire**.
- Otherwise, cut the **1st wire**.

### 4 Wires
- If there is more than one RED wire and the **last digit of the serial number is odd**, cut the **last RED wire**.
- Otherwise, if the last wire is YELLOW and there are no RED wires, cut the **1st wire**.
- Otherwise, if there is exactly one BLUE wire, cut the **1st wire**.
- Otherwise, cut the **2nd wire**.

### 5 Wires
- If the last wire is BLACK and the **last digit of the serial number is odd**, cut the **4th wire**.
- Otherwise, if there is exactly one RED wire and more than one YELLOW wire, cut the **1st wire**.
- Otherwise, if there are no BLACK wires, cut the **2nd wire**.
- Otherwise, cut the **1st wire**.

### 6 Wires
- If there are no YELLOW wires and the **last digit of the serial number is odd**, cut the **3rd wire**.
- Otherwise, if there is exactly one YELLOW wire and more than one WHITE wire, cut the **4th wire**.
- Otherwise, if there are no RED wires, cut the **last wire**.
- Otherwise, cut the **4th wire**.

---

## MODULE 2: KEYPAD

The defuser will see 4 symbols on the screen. They must read out all four symbol names. Find the **one column below** that contains all four of the defuser's symbols, then tell them to press the symbols in that column's **top-to-bottom order**.

| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 | Column 6 |
|----------|----------|----------|----------|----------|----------|
| BOLT     | MOON     | GEAR     | STAR     | DART     | COIL     |
| STAR     | BOLT     | WAVE     | KNOT     | MOON     | GEAR     |
| DROP     | RING     | KNOT     | FANG     | COIL     | MOON     |
| GEAR     | WAVE     | DART     | RING     | APEX     | FANG     |
| KNOT     | STAR     | MOON     | GEAR     | DROP     | BOLT     |
| RING     | COIL     | DROP     | APEX     | FANG     | WAVE     |
| DART     | FANG     | APEX     | COIL     | BOLT     | KNOT     |

**Example:** If the defuser says "WAVE, DART, GEAR, KNOT", find Column 3 (which contains all four). The correct press order is: GEAR → WAVE → KNOT → DART.

---

## MODULE 3: THE BUTTON

The defuser will see a large colored button with a word on it. They must tell you the **button's color** and the **word on the button**.

### Step 1: Determine the action

Follow these rules **in order** — use the first rule that applies:

1. If the button is **BLUE** and the label says **"ABORT"** → **hold the button**.
2. If the label says **"DETONATE"** → **tap the button** (press and immediately release).
3. If the button is **WHITE** and the **serial number contains a vowel (A, E, I, O, U)** → **hold the button**.
4. If the button is **RED** and the label says **"HOLD"** → **tap the button**.
5. If none of the above apply → **hold the button**.

### Step 2: If holding the button

When the defuser holds the button (press GREEN and keep it held), a **colored strip** will appear. The defuser must tell you the strip's color, then release (press START) when the **countdown timer has a specific digit in the ones place**:

| Strip Color | Release when timer ones digit is: |
|-------------|----------------------------------|
| BLUE        | 4                                |
| YELLOW      | 5                                |
| Any other   | 1                                |

**Example:** If the strip is BLUE, the defuser should release when the timer shows any time ending in 4 (like 2:34, 1:14, 0:04, etc.).

---

## MODULE 4: MORSE CODE

The defuser will see a flashing light and the morse code pattern displayed as dots and dashes. They must read the **morse code pattern** to you. Decode the word, then look up the correct frequency.

### Morse Alphabet

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| .- | -... | -.-. | -.. | . | ..-. | --. | .... | .. |

| J | K | L | M | N | O | P | Q | R |
|---|---|---|---|---|---|---|---|---|
| .--- | -.- | .-.. | -- | -. | --- | .--. | --.- | .-. |

| S | T | U | V | W | X | Y | Z |
|---|---|---|---|---|---|---|---|
| ... | - | ..- | ...- | .-- | -..- | -.-- | --.. |

### Frequency Table

| Word   | Frequency (MHz) |
|--------|----------------|
| SHELL  | 3.505          |
| HALLS  | 3.515          |
| SLICK  | 3.522          |
| TRICK  | 3.532          |
| BOXES  | 3.535          |
| LEAKS  | 3.542          |
| STROBE | 3.545          |
| BISTRO | 3.552          |
| FLICK  | 3.555          |
| BOMBS  | 3.565          |
| BREAK  | 3.572          |
| BRICK  | 3.575          |
| STEAK  | 3.582          |
| STING  | 3.592          |
| VECTOR | 3.595          |
| BEATS  | 3.600          |

Tell the defuser the correct frequency. They will tune to it using UP/DOWN and submit with GREEN.

---

## MODULE 5: SIMON SAYS

The defuser will see four colored lights (RED, BLUE, GREEN, YELLOW) that flash in a sequence. The defuser must repeat the sequence — but with **remapped colors** based on the current number of strikes and whether the **serial number contains a vowel**.

The defuser's buttons for colors are:
- **UP** = RED
- **START** = BLUE
- **DOWN** = GREEN
- **GREEN button** = YELLOW

### If the serial number DOES NOT contain a vowel (A, E, I, O, U):

| Strikes | Flashes RED → Press | Flashes BLUE → Press | Flashes GREEN → Press | Flashes YELLOW → Press |
|---------|--------------------|--------------------|---------------------|----------------------|
| 0       | BLUE               | RED                | YELLOW              | GREEN                |
| 1       | YELLOW             | GREEN              | BLUE                | RED                  |
| 2       | GREEN              | YELLOW             | RED                 | BLUE                 |

### If the serial number DOES contain a vowel:

| Strikes | Flashes RED → Press | Flashes BLUE → Press | Flashes GREEN → Press | Flashes YELLOW → Press |
|---------|--------------------|--------------------|---------------------|----------------------|
| 0       | BLUE               | YELLOW             | GREEN               | RED                  |
| 1       | GREEN              | BLUE               | RED                 | YELLOW               |
| 2       | YELLOW             | RED                | BLUE                | GREEN                |

The module has multiple stages. In stage 1, one color flashes. In stage 2, two colors flash (the original plus one more), and so on. Each stage, you must enter the **entire sequence from the beginning** using the mapping for your **current** strike count.

---

## MODULE 6: NUMBER PAD

The defuser will see a **display showing a number (1–4)** and a set of **indicator lights** (labeled SIG, FRK, CAR, IND, MSA, BOB — some lit, some unlit). They must tell you: the **display number** and **which indicators are lit**.

Based on these, tell the defuser which number to select:

### Display shows 1:
- If **FRK** is lit and the **last digit of the serial is odd** → select **3**
- Otherwise, if **CAR** is lit → select **4**
- Otherwise → select **2**

### Display shows 2:
- If **SIG** and **FRK** are both lit → select **4**
- Otherwise, if the **last digit of the serial is odd** → select **1**
- Otherwise → select **3**

### Display shows 3:
- If **CAR** is lit and the **last digit of the serial is even** → select **1**
- Otherwise, if **SIG** is lit → select **2**
- Otherwise → select **4**

### Display shows 4:
- If **FRK** and **CAR** are both lit → select **2**
- Otherwise, if **SIG** is lit and the **last digit of the serial is odd** → select **3**
- Otherwise → select **1**

---

## GENERAL TIPS

- The defuser navigates between modules using RED (previous) and BLUE (next).
- Modules can be solved in any order.
- A wrong answer on any module counts as a **strike**. Three strikes = detonation.
- Stay calm, communicate clearly, and watch the timer.

---

*Good luck. Don't blow up.*
