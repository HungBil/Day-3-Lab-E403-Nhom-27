# Flowchart: ReAct Travel Planner Agent

## Diagram 1: Kien truc tong quan

```mermaid
flowchart LR
    A[Nguoi dung\nchat.html] -->|POST api/chat| B[Backend Server\napp.py]
    B -->|agent.run| C[ReAct Agent\nagent.py v2]
    C -->|generate| D[LLM Provider\nGPT / Gemini]
    D -->|content usage latency| C
    C -->|execute_tool| E[Travel Tools\n6 functions]
    E -->|observation| C
    C -->|log_event\ntrack_request| F[Telemetry\nlogger + metrics]
    B -->|reply traces steps| A
```

---

## Diagram 2: ReAct Loop chinh

```mermaid
flowchart TD
    S([Nguoi dung gui cau hoi])
    S --> I[Khoi tao\nsteps = 0\ntraces = empty\nprompt = User Question]
    I --> G{steps < max_steps}

    G -->|Het buoc| T[AGENT END\nmax steps reached\nTra partial answer]
    T --> RF([Ket qua: max steps reached])

    G -->|Con buoc| ST[steps = steps + 1]
    ST --> L[LLM generate\nprompt + system prompt]

    L -->|Exception| LE[LLM ERROR\nAPI timeout / rate limit]
    LE --> RE([Ket qua: error])

    L -->|OK| TR[Track metrics\ntokens + latency]
    TR --> P{Phan tich\nLLM output}

    P -->|Thay Final Answer| FA[Trich xuat answer\nCat trailing Thought]
    FA --> RO([Ket qua: success\nanswer + traces])

    P -->|Thay Action tool| EX[Thuc thi tool\nexecute tool name args]
    EX --> AP[Noi vao prompt\nObservation: result\nContinue reasoning]
    AP --> G

    P -->|Khong thay gi| PE[PARSE ERROR\nNudge LLM\nDung dung dinh dang]
    PE --> G
```

---

## Diagram 3: Xu ly tool va loi

```mermaid
flowchart TD
    IN[execute tool\ntool name + args str]
    IN --> LK{Tool co trong\nTOOL REGISTRY?}

    LK -->|Khong| HL[Tool not found\nHallucination detected]
    HL --> OE[Observation = error msg\nLLM tu sua buoc tiep]

    LK -->|Co| PA[parse args\n1. JSON array\n2. ast literal eval\n3. Regex comma split]
    PA -->|Loi parse| PE[Failed to parse args]
    PE --> OE

    PA -->|So arg sai| CE[Expected N args got M]
    CE --> OE

    PA -->|OK| FC[Goi ham tool]
    FC -->|Data tim thay| OK[Observation ket qua\nvi du: Hotel 3 sao 500k dem]
    FC -->|Data khong ton tai| NF[No data found for X]
    FC -->|Sai kieu du lieu| TE[Invalid value abc]

    OK --> RT[Tra ve observation string]
    NF --> RT
    OE --> RT
    TE --> RT
```

---

## Diagram 4: Domain Guardrail

```mermaid
flowchart TD
    U[User gui tin nhan] --> CK{Kiem tra\nnoi dung}

    CK -->|Ngon tu thieu ton trong| RD1[Final Answer ngay\nVui long su dung\nngon ngu lich su\nGoi y diem den du lich]

    CK -->|Ngoai pham vi du lich\nvi du: mua xe VinFast| RD2[Final Answer ngay\nToi chi ho tro\nlap ke hoach du lich\nBan muon di dau?]

    CK -->|Du lich Viet Nam| OK2[Thuc hien ReAct Loop\nGoi tools tra ket qua]
    OK2 --> FA[Final Answer bang tieng Viet\nDung tieng Anh]
```

---

## Diagram 5: 5 Use Case luong chay

```mermaid
flowchart LR
    subgraph TC1 [TC1 Multi step Da Nang thang]
        direction TB
        t1a[search destination Da Nang]
        t1b[search attraction Da Nang beach]
        t1c[get hotel price Da Nang 3 3]
        t1d[estimate food cost Da Nang 3 mid]
        t1e[check budget 3800000 5000000]
        t1a --> t1b --> t1c --> t1d --> t1e
    end

    subgraph TC2 [TC2 Budget tran Phu Quoc 5 sao]
        direction TB
        t2a[search destination Phu Quoc]
        t2b[get hotel price Phu Quoc 5 3]
        t2c[check budget 7500000 1000000]
        t2d[VUOT NGAN SACH 6.5 trieu]
        t2a --> t2b --> t2c --> t2d
    end

    subgraph TC3 [TC3 Cau don gian Sa Pa]
        direction TB
        t3a[get weather Sapa 12]
        t3b[Final Answer 5-15 do C]
        t3a --> t3b
    end

    subgraph TC4 [TC4 So sanh 2 noi]
        direction TB
        t4a[search destination Hoi An]
        t4b[search destination Nha Trang]
        t4c[search attraction Hoi An culture]
        t4d[get hotel price x2]
        t4e[So sanh ket qua]
        t4a --> t4b --> t4c --> t4d --> t4e
    end

    subgraph TC5 [TC5 Input mo ho]
        direction TB
        t5a[Khong co ten thanh pho]
        t5b[Final Answer ngay\nGoi y Da Nang\nPhu Quoc Hoi An]
        t5a --> t5b
    end
```
