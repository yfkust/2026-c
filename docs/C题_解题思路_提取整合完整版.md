# 2026 年中国研究生数学建模竞赛 C 题：解题思路

> 题目：**服务于脑机接口与精神性疾病诊断的脑电图计算模型**   

---

# 1. 题目本质、三问关系与总体主线

## 1.1 C 题真正要求解决什么

这道题并不是一个普通的“脑电分类题”。题目把问题从数据层一直推到机理层和认知层，核心目标是建立一个能够连接：

\[
\text{视觉刺激}
\rightarrow
\text{神经系统响应}
\rightarrow
\text{头皮 EEG}
\rightarrow
\text{认知过程与行为}
\]

的计算模型。

赛题给出的三问可以概括为：

1. **问题一：数据层。**  
   从 F3、Fz、F4 三个前额区 EEG 通道中，在存在眨眼、运动、背景脑电等强干扰的情况下，提取与视觉刺激相关的有效响应，并且特别要求：**降噪不能把反映左右三角形形状差异的脑电特征一起消掉。**

2. **问题二：机理层。**  
   建立从 **LGN（外侧膝状体）→ 视觉皮层/皮层神经群 → 头皮 EEG** 的生成模型，解释为什么左右三角形会产生不同的 EEG，并给出能够区分左右刺激的特征表示。

3. **问题三：认知层。**  
   在第二问的信号形成机制基础上，进一步加入记忆、注意、匹配、决策等过程，建立宏观认知模型，并用 EEG 和行为数据进行验证。

因此三问不应割裂。推荐的全文主线是：

\[
\boxed{
\text{保留形状信息的脑电去噪}
\rightarrow
\text{解释形状差异的神经动力学}
\rightarrow
\text{感觉与记忆共同驱动的认知模型}
}
\]

---

## 1.2 两个实验项目必须严格区分

题目设计了两个视觉认知项目。

### 项目一：目标位置提前已知

目标出现前，受试者已经知道目标位于左侧还是右侧，只需要等待目标出现并作出相应操作。

这意味着该项目的认知负荷更偏向：

- 已建立空间预期；
- 等待目标；
- 目标出现后完成较快的确认与动作。

### 项目二：位置未知，只知道目标形状

目标出现前并不知道目标最终位于左侧还是右侧，只知道应该寻找哪一种方向的三角形。

这意味着项目二需要更多的：

- 形状模板保持；
- 目标出现后的视觉匹配；
- 位置选择；
- 随后的行为决策。

因此，两个项目虽然都包含“左右三角形”，但并不是同一个认知任务。

**重要：不能预设项目二的 P300 一定比项目一大。**

`2026思路.docx` 前半部分曾给出“项目二 P300 应大于项目一”这样的早期直觉，但文档后半部分明确修正：任务难度、刺激概率、时间结构等都会影响 P300，因此这只能作为待检验假设，不能写成建模约束或先验结论。

---

# 2. 数据、事件与建模约束

## 2.1 数据通道

题目说明每份数据包含 10 个通道：

\[
[\text{Fz},\text{F3},\text{F4},
\text{FzDecon},\text{F3Decon},\text{F4Decon},
\text{ECG},\text{VisCue},\text{TgtAct},\text{TimeStamp}]
\]

采样率为：

\[
f_s = 256 \text{ Hz}
\]

其中：

- 通道 1–3：原始脑电 Fz、F3、F4；
- 通道 4–6：设备自带处理后的 Decon 数据；
- 通道 7：参考/辅助记录；
- 通道 8：视觉提示；
- 通道 9：目标/应答相关标记；
- 通道 10：时间戳。

### 最重要的数据使用原则

**主模型必须以通道 1–3 的原始 EEG 为输入。**

题目明确指出，通道 4–6 的机器去干扰结果可能在去除噪声时同时破坏视觉响应特征，因此不能把这些数据直接作为最终输入，更不能把它们当成“无噪声真值”。

---

## 2.2 对附件的核验结果

对四份实验记录进行了事件统计，并给出了如下结果：

| 数据记录 | 原始 EEG 通道 | 视觉提示数 | 左提示 | 右提示 |
|---|---|---:|---:|---:|
| VisualCogA_Task-1 | Fz、F3、F4 | 100 | 54 | 46 |
| VisualCogA_Task-2 | Fz、F3、F4 | 100 | 57 | 43 |
| VisualCogB_Task-1 | Fz、F3、F4 | 100 | 48 | 52 |
| VisualCogB_Task-2 | Fz、F3、F4 | 100 | 50 | 50 |

因此四份记录合计具有 400 次视觉提示事件。

### 约束 1：第 4–6 通道不能当真值

不能做：

\[
\text{Raw EEG}
\rightarrow
\text{拟合 Decon EEG}
\]

因为这相当于把题目明确质疑的方法重新当成标签。

---

### 约束 2：第 9 通道编码不能机械照搬题面文字

- 项目一中第 9 通道主要出现持续的 \(\pm1\)；
- 项目二中同时存在持续的 \(\pm1\) 和单点 \(\pm2\)；
- 持续标记通常在提示约 2.215 s 后出现，与实验中目标出现时序较接近。

因此不能简单地写：

> “TgtAct 第一次非零就是点击时间。”

必须先建立事件解释规则，并把存在不确定性的事件边界在论文中明确说明。

---

### 约束 3：存在疑似 \(\pm 1000\) 饱和限幅

原始 EEG 中存在大量恰好取值为 \(\pm1000\) 的样本。

如果这确实来自采集设备限幅，则原始幅值信息已经丢失，不能通过平滑或插值声称“恢复真实信号”。

因此应建立：

\[
M_{c,t}
=
\begin{cases}
0,& |x_c(t)|=1000 \text{ 或满足其他严重异常条件}\\
1,& \text{正常观测}
\end{cases}
\]

作为质量掩码。

严重限幅片段应：

- 剔除；
- 或在模型拟合中降权；
- 或按缺失观测处理。

---

### 约束 4：项目二不能用“提示方向 = 点击方向”判正确

项目二中的提示方向表示的是**目标形状**，最终目标可能出现在左侧，也可能在右侧。

所以：

\[
\text{提示方向}
\neq
\text{目标空间位置}
\]

二者必须作为不同变量。

---

### 约束 5：只有三个额区 EEG 通道

F3、Fz、F4 是低维头皮观测。

这意味着：

- 可以建立低维有效神经群模型；
- 可以讨论某个潜在状态具有“记忆/海马功能解释”；
- 但不能声称仅依靠三个额区通道无约束地恢复出了全脑神经元空间分布；
- 也不能把某个拟合隐变量直接称为“实测海马体信号”。

这条约束对第二问和第三问尤其重要。

---

# 3. 整体建模框架

建议采用四层框架。

```text
第 0 层：数据审计
    ↓
事件表 + 质量掩码 + 训练/验证划分
    ↓
第 1 层：保特征脑电去噪
    ↓
单试次响应 + ERP + 时频特征
    ↓
第 2 层：LGN—皮层—头皮生成模型
    ↓
形状选择性神经状态 + 头皮 EEG 预测
    ↓
第 3 层：感觉—记忆—决策认知模型
    ↓
EEG + 反应时/行为联合预测
```

其中：

- 第一问解决“**观测数据是否可信**”；
- 第二问解决“**这个波形为什么这样产生**”；
- 第三问解决“**这些神经状态如何参与认知和行为**”。

---

# 4. 问题一：保留视觉形状信息的脑电降噪与响应提取

## 4.1 问题一真正要证明的两件事

问题一不是“滤波后画一条更漂亮的曲线”。

必须同时证明：

\[
\boxed{\text{噪声减少}}
\]

以及

\[
\boxed{\text{视觉形状相关信息仍然被保留}}
\]

如果只有前者，不能充分回应题目“去伪影同时保留视物特征”的核心要求。

---

## 4.2 观测信号模型

设第 \(i\) 个 trial、第 \(c\) 个通道的脑电为：

\[
X_{i,c}(t)
=
S_{i,c}(t)+A_{i,c}(t)+R_{i,c}(t)
\]

其中：

- \(S_{i,c}(t)\)：任务相关脑电响应；
- \(A_{i,c}(t)\)：眨眼、运动、瞬态异常等结构化伪影；
- \(R_{i,c}(t)\)：背景脑活动和剩余噪声。

进一步，为保留 trial 差异，可把任务响应拆成：

\[
S_{i,c}(t)
=
S^{\mathrm{common}}_{q,y,c}(t)
+
S^{\mathrm{var}}_{i,c}(t)
\]

其中：

- \(q\)：项目 1 / 项目 2；
- \(y\)：左 / 右三角形；
- \(S^{\mathrm{common}}\)：重复 trial 中稳定出现的共同响应；
- \(S^{\mathrm{var}}\)：单试次幅值、潜伏期和波形差异。

这比单纯假设：

\[
X = \text{ERP模板}+\text{噪声}
\]

更符合题目要求，因为“左右三角形差异”和“单试次认知差异”本身就是需要保留的信息。

---

## 4.3 Step 1：事件表构建

推荐建立统一事件表：

| trial | task | cue_onset | cue_type | target_onset | response_time | response_code | quality |
|---:|---:|---:|---:|---:|---:|---:|---|

首先以 VisCue 的变化定位视觉提示。

若：

\[
v(t-1)=0,\quad v(t)\in\{-1,+1\}
\]

则把 \(t\) 视为 cue onset。

对于第 9 通道，不能统一套一个规则，而应：

1. 分 Task-1 / Task-2；
2. 分析持续标记与瞬时标记；
3. 根据实验时序推断 candidate target onset / response onset；
4. 对不确定事件增加 `event_confidence` 标记。

这是整篇建模的第一个关键点，因为第三问的反应时模型高度依赖事件边界。

---

## 4.4 Step 2：Epoch 截取

提示锁定分析可从：

\[
[-200,800]\text{ ms}
\]

或：

\[
[-200,1000]\text{ ms}
\]

开始。

重点观察题目明确给出的：

\[
250\sim500\text{ ms}
\]

P300 候选区间。

但不应只保留 250–500 ms，因为：

- 0–200 ms 可能包含早期视觉加工；
- 200–400 ms 可能反映注意/识别；
- 400 ms 后可能包含后续比较、决策或运动准备。

同时建议建立第二套 **target-locked epoch**，分析目标出现后的脑电，而不是只分析 cue-locked EEG。

---

## 4.5 Step 3：质量控制

对每个“trial × channel”检查：

### （1）限幅

\[
|x(t)|=1000
\]

出现比例。

### （2）平直

若：

\[
\operatorname{std}(x[t_1:t_2]) < \epsilon
\]

则可能为掉线或平直异常。

### （3）突跳

利用一阶差分：

\[
d(t)=x(t)-x(t-1)
\]

检测极端变化。

### （4）极端幅度

传统 EEG 中可使用幅度阈值作为候选规则，但本题不能机械固定 \(\pm100\mu V\)，除非确认数据单位。

因此更稳妥的是使用：

\[
|x-\operatorname{median}(x)|
>
k\cdot \operatorname{MAD}(x)
\]

其中 MAD 为 median absolute deviation。

---

# 5. 问题一基线方案：温和滤波 + 小波 + 稳健 ERP

这是最容易实现、最适合作为论文基线的方法。

## 5.1 温和滤波

给出了 0.1–30 Hz 或 1–30 Hz 等候选范围。最终建议从：

\[
0.1\sim30 \text{ Hz}
\]

开始测试。

不能为了“让 P300 看起来更明显”而不断提高高通截止频率，因为这样可能改变 ERP 的慢波形态。

工频滤波也不应机械添加。先画 PSD：

\[
P_{xx}(f)
\]

如果 50 Hz 附近确实存在明显窄带峰，再增加 notch。

---

## 5.2 基线校正

对刺激前：

\[
[-200,0]\text{ ms}
\]

计算：

\[
b_{i,c}
=
\frac{1}{T_b}
\sum_{t\in \mathcal B}
x_{i,c}(t)
\]

然后：

\[
x'_{i,c}(t)
=
x_{i,c}(t)-b_{i,c}
\]

---

## 5.3 小波软阈值

采用离散小波：

\[
x(t)
=
\sum_k a_{J,k}\phi_{J,k}(t)
+
\sum_{j=1}^{J}\sum_k d_{j,k}\psi_{j,k}(t)
\]

对高频噪声系数使用软阈值：

\[
\hat d_{j,k}
=
\operatorname{sgn}(d_{j,k})
\max(|d_{j,k}|-\lambda_j,0)
\]

建议使用 SURE：

\[
\lambda_j
=
\lambda^{\text{SURE}}_j
\]

自动选择阈值。

但“保特征”版本不应对所有时间位置使用完全相同的收缩强度。

可以定义：

\[
\lambda_{j,k}
=
\lambda_j(1-\rho_{j,k})
\]

其中：

\[
0\le \rho_{j,k}\le1
\]

表示训练数据中该时频区域的任务相关稳定程度。

任务相关越强，阈值越小。

---

## 5.4 稳健事件平均

普通 ERP：

\[
ERP_c(t)
=
\frac{1}{N}
\sum_i x_{i,c}(t)
\]

容易被少量异常 trial 影响。

推荐加权：

\[
ERP_c(t)
=
\frac{\sum_i w_i x_{i,c}(t)}
{\sum_iw_i}
\]

其中 \(w_i\) 由 trial 质量决定。

例如：

\[
w_i
=
\exp(-\gamma Q_i)
\]

\(Q_i\) 为该 trial 的异常程度。

---

# 6. 问题一推荐高级方案：结构化稳健分解

## 6.1 张量表示

把数据表示成：

\[
\mathcal X
\in
\mathbb R^{C\times T\times N}
\]

其中：

- \(C=3\)：F3、Fz、F4；
- \(T\)：epoch 时间点；
- \(N\)：trial 数量。

建立：

\[
\boxed{
\mathcal X
=
\mathcal L
+
\mathcal V
+
\mathcal A
+
\mathcal R
}
\]

其中：

- \(\mathcal L\)：共同的低维任务响应；
- \(\mathcal V\)：trial-specific variation；
- \(\mathcal A\)：成段/局部伪影；
- \(\mathcal R\)：剩余背景活动。

---

## 6.2 目标函数

可以写为：

\[
\min_{\mathcal L,\mathcal V,\mathcal A}
\frac12
\left\|
M\odot
(\mathcal X-\mathcal L-\mathcal V-\mathcal A)
\right\|_F^2
+
\lambda_L\|\mathcal L\|_*
+
\lambda_A\|\mathcal A\|_{2,1}
+
\lambda_V \mathcal R_V(\mathcal V)
+
\lambda_S\mathcal R_S(\mathcal L)
\]

其中：

- \(M\)：质量掩码；
- \(\|\mathcal L\|_*\)：低秩约束；
- \(\|\mathcal A\|_{2,1}\)：鼓励伪影成段出现；
- \(\mathcal R_V\)：限制 trial 变化的复杂度；
- \(\mathcal R_S\)：响应曲线平滑约束。

---

## 6.3 为什么这个模型比普通 RPCA 更合适

如果只写：

\[
X=L+S
\]

并把“非共同部分”全部当成稀疏异常，就可能把：

- 左右刺激真实差异；
- 单试次潜伏期变化；
- 单试次 ERP 幅值差异；

一起当成噪声删掉。

因此单独设置：

\[
\mathcal V
\]

是本题“保形降噪”的核心设计之一。

---

## 6.4 潜伏期抖动

设第 \(i\) 个 trial 的延迟为 \(\delta_i\)，则：

\[
S_i(t)
=
a_i S_0(t-\delta_i)
+
v_i(t)
\]

其中：

- \(a_i\)：trial 增益；
- \(\delta_i\)：潜伏期偏移；
- \(v_i(t)\)：剩余变化。

可以在训练阶段交替估计：

1. 模板 \(S_0\)；
2. 单试次增益 \(a_i\)；
3. 潜伏期 \(\delta_i\)；
4. 伪影项。

注意：潜伏期对齐只是估计工具，\(\delta_i\) 本身仍然是认知特征，不能永久丢掉。

---

# 7. P300/ERP 曲线拟合

题目要求“拟合相应曲线”。

建议不要只找一个最大值，而使用“稳健 ERP + 平滑拟合”。

## 7.1 三次平滑样条

拟合：

\[
\hat f
=
\arg\min_f
\left[
\sum_{n}
(y_n-f(t_n))^2
+
\lambda
\int
(f''(t))^2dt
\right]
\]

这样能够避免高阶多项式振荡。

---

## 7.2 高斯峰模型

如果希望把 ERP 峰做参数化，可使用：

\[
f(t)
=
b_0+b_1t+
\sum_{m=1}^{M}
A_m
\exp
\left[
-\frac{(t-\mu_m)^2}{2\sigma_m^2}
\right]
\]

其中：

- \(A_m\)：峰幅值；
- \(\mu_m\)：峰潜伏期；
- \(\sigma_m\)：峰宽。

不要使用过大的 \(M\)，否则容易把噪声拟合成生理峰。

---

# 8. 问题一特征设计

对每个：

\[
(\text{task},\text{cue},\text{channel})
\]

提取：

### 时间域

- 250–500 ms 平均幅值；
- 峰值；
- 峰潜伏期；
- AUC；
- 上升斜率；
- 峰宽。

### 空间域

推荐三个可逆对比：

\[
C_1(t)=\frac{F3(t)+F4(t)}2
\]

\[
C_2(t)=F4(t)-F3(t)
\]

\[
C_3(t)=Fz(t)-\frac{F3(t)+F4(t)}2
\]

其中 \(C_2\) 可以作为额区左右差异指标，但不能直接解释为精确脑源定位。

也可定义侧化指数：

\[
LI=
\frac{A_{F4}-A_{F3}}
{|A_{F4}|+|A_{F3}|+\varepsilon}
\]

---

## 8.1 时频特征

使用 CWT：

\[
W_x(a,b)
=
\frac1{\sqrt a}
\int x(t)
\psi^*
\left(
\frac{t-b}{a}
\right)dt
\]

重点分析：

- delta：1–4 Hz；
- theta：4–8 Hz；
- alpha：8–13 Hz；
- beta：13–30 Hz。

提到 PLV；但如果只是同一事件重复试次，更适合用跨试次相位一致性：

\[
ITPC(f,t)
=
\left|
\frac1N
\sum_{i=1}^{N}
e^{j\phi_i(f,t)}
\right|
\]

注意：

ITPC 是一个**试次集合指标**，不能说每个单试次都独立拥有一个 ITPC。

---

# 9. 问题一必须做的验证

## 9.1 去噪效果

比较：

- baseline 波动；
- 极端幅度比例；
- trial-to-trial variability；
- ERP 稳定性。

---

## 9.2 波形保真：半模拟实验

没有真实“干净脑电”时，可以构造：

\[
X^{sim}
=
S^{known}
+
B^{real}
+
A^{sim}
\]

其中：

- \(S^{known}\)：人工设定的 ERP；
- \(B^{real}\)：真实数据中的低伪影背景；
- \(A^{sim}\)：人工眨眼/脉冲/限幅等伪影。

比较：

\[
E_A
=
\frac{|\hat A-A|}{|A|}
\]

\[
E_\tau
=
|\hat \tau-\tau|
\]

\[
E_{\mathrm{AUC}}
=
\frac{|\widehat{\mathrm{AUC}}-\mathrm{AUC}|}
{|\mathrm{AUC}|}
\]

用于证明算法不是“把波形做漂亮”。

---

## 9.3 信息保留

可以用简单的：

- shrinkage LDA；
- logistic regression；
- linear SVM；

作为验证工具。

但分类器只是：

\[
\text{information probe}
\]

不是主模型。

必须采用 trial-level cross-validation。

所有：

- 标准化参数；
- 波形模板；
- 小波阈值；
- 降噪字典；
- 特征选择；

都只能由训练折估计。

---

## 9.4 标签置乱

随机打乱左右 cue：

\[
y_i^{perm}
=
\pi(y_i)
\]

重新运行分类/差异分析。

如果置乱后仍然能得到很高的“左右判别”，可能存在：

- 数据泄漏；
- 时间漂移；
- 眼动混杂；
- event encoding 泄漏。

---

# 10. 问题二：LGN—皮层—头皮 EEG 的形成机制

问题二不能只训练一个 CNN 判断左右。

它需要回答：

> 左右三角形的几何差异如何通过视觉系统映射成不同的皮层活动，并最终在 F3/Fz/F4 形成不同 EEG？

建议的通路描述为：

\[
\boxed{
\text{Retina}
\rightarrow
\text{LGN}
\rightarrow
\text{V1 / 视觉皮层}
\rightarrow
\text{高阶视觉/认知网络}
\rightarrow
\text{等效偶极源}
\rightarrow
\text{Volume Conduction}
\rightarrow
F3,Fz,F4
}
\]

不要把视觉通路简单写成“LGN 直接到额叶”。

---

# 11. 形状编码：为什么左右三角形会不同

左右三角形属于镜像刺激。

因此面积、周长等全局量可能相同：

\[
A_L=A_R
\]

\[
P_L=P_R
\]

所以不能靠这些特征解释神经差异。

真正需要编码的是：

- 边缘方向；
- 顶点方向；
- 局部边缘的位置；
- 多个局部特征之间的空间构型。

---

## 11.1 LGN：中心—周围编码

可使用 DoG 模型：

\[
h(x,y)
=
\frac1{2\pi\sigma_c^2}
e^{-\frac{x^2+y^2}{2\sigma_c^2}}
-
\kappa
\frac1{2\pi\sigma_s^2}
e^{-\frac{x^2+y^2}{2\sigma_s^2}}
\]

视觉输入：

\[
I_{LGN}
=
I*h
\]

用于表示局部亮度对比。

---

## 11.2 V1：Gabor 方向选择性

定义：

\[
G_\theta(x,y)
=
\exp
\left[
-\frac{x'^2+\gamma^2 y'^2}{2\sigma^2}
\right]
\cos
\left(
2\pi\frac{x'}{\lambda}+\phi
\right)
\]

其中：

\[
x'=x\cos\theta+y\sin\theta
\]

\[
y'=-x\sin\theta+y\cos\theta
\]

对左右刺激：

\[
R_\theta
=
I_{LGN}*G_\theta
\]

得到各方向通道响应。

---

## 11.3 构型编码

仅有方向直方图仍可能无法区分镜像。

因此进一步定义：

\[
\mathbf f
=
[
E_{\theta_1,L},
E_{\theta_1,R},
\dots,
x_{\mathrm{tip}},
y_{\mathrm{tip}},
d_1,d_2,\dots
]
\]

其中：

- \(E_{\theta,L/R}\)：不同空间区域的方向能量；
- \(x_{\mathrm{tip}}\)：尖端相对中心的左右位置；
- \(d_k\)：局部轮廓之间的相对几何关系。

这一点与题目图 9 给出的启示一致：

> 物体识别并不只取决于“有哪些局部特征”，还依赖这些特征是否按照特定空间关系排列。

建议借鉴 COSFIRE 的思想，但如果没有完整实现 COSFIRE，应准确写成：

> “受 COSFIRE 构型选择性思想启发的 Gabor—构型编码”

而不是声称完整实现了原模型。

---

# 12. 问题二基础机理模型：Wilson–Cowan 神经群

对第 \(j\) 个神经群：

\[
\tau_E\frac{dE_j}{dt}
=
-E_j+
S_E
\left(
w_{EE}E_j
-
w_{EI}I_j
+
P_j(t)
+
\sum_kC^{E}_{jk}E_k
\right)
\]

\[
\tau_I\frac{dI_j}{dt}
=
-I_j+
S_I
\left(
w_{IE}E_j
-
w_{II}I_j
+
Q_j(t)
\right)
\]

其中：

- \(E_j(t)\)：兴奋神经群平均活动；
- \(I_j(t)\)：抑制神经群平均活动；
- \(\tau_E,\tau_I\)：时间常数；
- \(w_{EE}\)：自兴奋；
- \(w_{EI}\)：抑制对兴奋的作用；
- \(w_{IE}\)：兴奋对抑制的作用；
- \(w_{II}\)：自抑制；
- \(P_j(t)\)：视觉输入；
- \(C_{jk}\)：区域耦合。

Sigmoid：

\[
S(z)
=
\frac{1}{1+\exp[-a(z-\theta)]}
\]

左右刺激的主要生理参数尽量共享，只改变形状输入：

\[
P_j^{(L)}(t)
\neq
P_j^{(R)}(t)
\]

这样左右差异是由刺激构型自然产生，而不是分别拟合两套互不相关的模型。

---

# 13. 问题二推荐高级方案：低阶神经场

题目特别强调：不同视觉刺激可能引起不同神经元空间分布。

因此最终版本更推荐在 Wilson–Cowan 基础上引入有限空间结构。

## 13.1 神经场

设皮层位置为 \(\mathbf r\)。

\[
\tau_E
\frac{\partial E(\mathbf r,t)}{\partial t}
=
-E(\mathbf r,t)
+
S_E
\left[
\int_\Omega
w_{EE}(\mathbf r,\mathbf r')
E(\mathbf r',t-\tau_{\mathbf rr'})
d\mathbf r'
-
\int_\Omega
w_{EI}(\mathbf r,\mathbf r')
I(\mathbf r',t)
d\mathbf r'
+
P(\mathbf r,t)
\right]
\]

\[
\tau_I
\frac{\partial I(\mathbf r,t)}{\partial t}
=
-I(\mathbf r,t)
+
S_I[\cdots]
\]

左右三角形通过：

\[
P_L(\mathbf r,t)
\]

和：

\[
P_R(\mathbf r,t)
\]

产生不同空间模式。

---

## 13.2 为什么必须降阶

只有 F3、Fz、F4 三个通道，因此不能估计一个几千维的神经场。

推荐使用：

\[
E(\mathbf r,t)
=
\sum_{k=1}^{K}
a_k(t)\phi_k(\mathbf r)
\]

其中：

\[
K\ll T
\]

例如只保留：

- common mode；
- left-right difference mode；
- central integration mode。

通过 Galerkin 投影：

\[
\langle \phi_m,\mathcal F(E,I)\rangle
\]

把 PDE 降为低维 ODE。

这样可以在保持空间机制的同时控制参数数量。

---

# 14. 从神经群到 EEG：正向观测模型

这是问题二不可缺失的一步。

不能写：

\[
EEG(t)=E(t)
\]

因为神经元平均发放率不是头皮电压。

先构造等效突触/偶极源：

\[
q_j(t)
=
(h_s*E_j)(t)
\]

其中：

\[
h_s(t)
=
\frac{t}{\tau_s}
e^{-t/\tau_s}u(t)
\]

是突触响应核。

然后：

\[
V_c(t)
=
\sum_{j=1}^{K}
L_{cj}q_j(t)
+
\epsilon_c(t)
\]

其中：

- \(V_c(t)\)：F3、Fz、F4；
- \(L_{cj}\)：有效 lead-field；
- \(q_j(t)\)：等效源；
- \(\epsilon_c\)：观测噪声。

神经场形式：

\[
V_c(t)
=
\int_\Omega
L_c(\mathbf r)
q(\mathbf r,t)
d\mathbf r
+
\epsilon_c(t)
\]

由于题目没有个体 MRI/头模型，最终论文中应将 \(L\) 称为：

> **受约束有效头皮投影矩阵**

而不是个体真实 lead field。

建议可用标准三层球头模做敏感性分析，但标准头模不能等同个体解剖真值。

---

# 15. 左右三角差异的形成机制

最终可以形成以下机制链：

\[
\boxed{
\text{左右镜像几何结构不同}
}
\]

导致：

\[
\boxed{
\text{Gabor方向响应的空间排列不同}
}
\]

导致：

\[
\boxed{
P_L(\mathbf r,t)
\neq
P_R(\mathbf r,t)
}
\]

导致：

\[
\boxed{
E_L(\mathbf r,t),I_L(\mathbf r,t)
\neq
E_R(\mathbf r,t),I_R(\mathbf r,t)
}
\]

再经过：

\[
q(\mathbf r,t)
\rightarrow
L_c(\mathbf r)
\]

形成：

\[
\boxed{
V_{F3}^{(L/R)}(t),
V_{Fz}^{(L/R)}(t),
V_{F4}^{(L/R)}(t)
}
\]

的差异。

特别注意：

> “左指向三角形”不等于“刺激出现在左视野”。

因此不能机械套用“左视野 → 右半球”的解释。

---

# 16. 问题二特征表示

分两类。

## 16.1 观测特征

\[
\mathbf z_{obs}
=
[
A_{F3},
A_{Fz},
A_{F4},
\tau_{F3},
\tau_{Fz},
\tau_{F4},
LI,
c_1,\dots,c_m
]
\]

其中 \(c_m\) 是 ERP 基函数系数或时频特征。

---

## 16.2 机制特征

\[
\mathbf z_{mech}
=
[
a_{\text{common}},
a_{\text{mirror}},
g,
\tau_{eff},
K_{EI},
\Lambda
]
\]

其中：

- \(a_{\text{common}}\)：共同模式；
- \(a_{\text{mirror}}\)：镜像差异模式；
- \(g\)：有效增益；
- \(\tau_{eff}\)：有效响应时间常数；
- \(K_{EI}\)：可靠可辨识的兴奋抑制指标；
- \(\Lambda\)：生成模型的左右证据。

---

# 17. 生成式左右分类

对一个未知 trial \(X\)，分别计算：

\[
p(X|H_L)
\]

和：

\[
p(X|H_R)
\]

定义：

\[
\boxed{
\Lambda(X)
=
\log p(X|H_R)
-
\log p(X|H_L)
}
\]

若：

\[
\Lambda>0
\]

则模型更支持右刺激；

若：

\[
\Lambda<0
\]

则模型更支持左刺激。

这比直接把神经场输出再丢进黑箱分类器更符合问题二的“计算模型”要求。

---

# 18. 问题二参数估计

建议采用 MAP：

\[
\hat\theta
=
\arg\min_\theta
\left[
\sum_{i,c,t}
w_{ict}
\left(
V_{ict}^{obs}
-
V_{ict}^{model}(\theta)
\right)^2
+
\lambda
\|\theta-\theta_0\|_{\Sigma_0^{-1}}^2
\right]
\]

其中：

- \(\theta_0\)：文献/生理合理初值；
- 参数有界；
- 使用多初值优化；
- 训练折内部调正则；
- 最后在留出 trial 检验预测。

---

# 19. 问题二必须做的参数可辨识性分析

因为：

\[
V=Lq
\]

存在尺度补偿：

\[
Lq=(\alpha L)(q/\alpha)
\]

所以必须固定：

- 一个源尺度；
- 或 lead-field 范数；
- 或某个参考增益。

否则“源幅值”和“投影权重”可以任意互相补偿。

还应做：

### 灵敏度

\[
S_k
=
\frac{\partial \hat V}{\partial \theta_k}
\]

### 多初值稳定性

比较不同初始值是否得到接近参数。

### 参数恢复

先人工设：

\[
\theta^\*
\]

生成模拟数据，再拟合 \(\hat\theta\)，检查：

\[
\hat\theta\approx\theta^\*
\]

只有稳定的参数才适合做生理解释。

---

# 20. 问题二关键消融

至少做：

### A. 去掉空间构型

只保留整体边缘能量。

如果左右区分显著下降，则证明：

\[
\text{spatial configuration}
\]

确有必要。

### B. 去掉抑制

令：

\[
w_{EI}=0
\]

观察波形解释能力。

### C. 集总模型 vs 神经场

比较：

\[
\text{Wilson-Cowan lumped}
\]

和：

\[
\text{low-order field}
\]

的留出预测。

### D. 镜像反事实

输入三角形做左右镜像，检查模型的差异模式是否随之系统改变。

---

# 21. 问题三：认知宏观模型

第三问的核心不是再独立建立一个新网络，而是：

\[
\text{继承第二问的感觉生成机制}
+
\text{增加记忆、注意、匹配和决策状态}
\]

完整 trial 应分成：

```text
提示阶段
    ↓
保持阶段
    ↓
目标出现
    ↓
匹配/比较
    ↓
决策
    ↓
运动准备
    ↓
点击
```

题目要求认知相关 EEG 的终点可以取：

\[
t_{resp}-100\text{ ms}
\]

但这应作为分析规则，并做：

\[
50,\ 100,\ 150 \text{ ms}
\]

敏感性分析。

---

# 22. 问题三基础模型：感觉—记忆—比较状态空间

定义：

\[
\mathbf z(t)
=
[
s(t),m(t),c(t)
]^\top
\]

其中：

- \(s(t)\)：感觉状态；
- \(m(t)\)：记忆保持状态；
- \(c(t)\)：比较/匹配状态。

可以写：

\[
\dot s
=
-\frac{s}{\tau_s}
+
G_su(t)
+
K_{ms}m
\]

\[
\dot m
=
-\frac{m}{\tau_m}
+
G_m s(t)
\]

\[
\dot c
=
-\frac{c}{\tau_c}
+
G_c\Phi(s,m,u_T)
\]

其中：

- \(u(t)\)：提示输入；
- \(u_T(t)\)：目标出现后的输入；
- \(\Phi\)：感觉和记忆匹配函数。

EEG：

\[
\mathbf y(t)
=
H_s s(t)
+
H_m m(t)
+
H_c c(t)
+
\epsilon(t)
\]

这里的 \(m(t)\) 可以赋予“与海马/记忆系统参与相关的潜在状态解释”，但不能称为直接重建出的海马 EEG。

---

# 23. Task-1 与 Task-2 的认知差异如何建模

不要完全建立两套模型。

用同一结构，不同任务门控：

\[
\dot{\mathbf z}
=
F(\mathbf z,u;\theta,\eta_q)
\]

其中：

\[
q\in\{1,2\}
\]

而 \(\eta_q\) 是少量 task modulation 参数。

例如：

### 项目一

提前知道目标位置，可允许较大的：

\[
g_{space}^{(1)}
\]

位置预期增益。

### 项目二

需要保持形状模板，可允许：

\[
\tau_m^{(2)}
\]

或：

\[
g_{shape}^{(2)}
\]

不同。

但哪些参数真的不同，应由模型比较决定，不能先写死。

---

# 24. 推荐高级认知模型：感觉—记忆反馈 + 证据累积

目标出现后定义决策变量：

\[
dx
=
v(s,m,T)dt
+
\sigma dW_t
\]

例如：

\[
v(t)
=
\beta_0
+
\beta_s s(t)
+
\beta_m m(t)
+
\beta_c c(t)
\]

当：

\[
x(t)\ge a
\]

或：

\[
x(t)\le -a
\]

到达决策边界。

反应时：

\[
RT
=
T_{decision}
+
T_{nd}
\]

其中：

- \(T_{decision}\)：证据首次到达阈值时间；
- \(T_{nd}\)：感觉传导和运动执行等非决策时间。

---

## 24.1 为什么不能从 cue onset 开始直接套 DDM

因为 cue 和 target 之间有题目人为规定的等待阶段。

若直接用：

\[
RT = t_{click}-t_{cue}
\]

并把这整段解释成决策时间，会把实验等待时间混进认知参数。

因此更合理的是：

\[
RT_{target}
=
t_{click}
-
t_{target}
\]

前提是 target onset 能够可靠解析。

---

# 25. EEG—行为联合拟合

定义参数：

\[
\Theta
=
[
\theta_{neural},
\theta_{memory},
\theta_{decision}
]
\]

联合似然：

\[
p(Y,RT|\Theta)
=
p(Y|\Theta)
p(RT|\Theta)
\]

MAP：

\[
\hat\Theta
=
\arg\max_\Theta
\left[
\log p(Y|\Theta)
+
\log p(RT|\Theta)
+
\log p(\Theta)
\right]
\]

但 EEG 每个 trial 有大量强相关时间点，不能把几千个采样点全当独立样本，否则 EEG 项会压倒行为项。

推荐先：

- PCA；
- spline basis；
- ERP component basis；

降维：

\[
Y(t)
\rightarrow
\mathbf c
\]

再构造 EEG likelihood。

---

# 26. 错误应答和漏答

赛题特别提醒：

> 应答可能错误，也可能不及时。

处理原则：

### 有独立正确标签

不要删掉错误 trial。

可以分析：

\[
p(\text{choice},RT,Y|\Theta)
\]

### 有截止时间但没有响应

视为右删失：

\[
T>T_{deadline}
\]

似然：

\[
P(T>T_{deadline})
=
1-F(T_{deadline})
\]

### 没有可靠正确答案标签

不要制造“正确率”。 项目二不能仅凭提示与点击符号同号就自动认为正确。

---

# 27. 第三问最重要的预测验证

不要只做：

> “模型拟合真实波形很好。”

要做真正预测。

## 固定前缀预测

例如目标出现后只使用前：

\[
T_p=300\text{ ms}
\]

EEG：

\[
Y[0:T_p]
\]

预测：

\[
RT-T_p
\]

或：

\[
RT
\]

不能对每个 trial 先看到真实 response time，再裁成：

\[
[t_{resp}-100\text{ ms}]
\]

然后用裁剪长度预测 RT。

这会发生严重未来信息泄漏。

---

# 28. 第三问竞争模型

推荐至少比较四个模型：

\[
M_0=\text{感觉}
\]

\[
M_1=\text{感觉}+\text{记忆}
\]

\[
M_2=\text{感觉}+\text{注意}
\]

\[
M_3=\text{感觉}+\text{记忆}+\text{注意}
\]

比较：

- held-out EEG RMSE；
- RT MAE；
- NLL；
- 参数稳定性。

只有当：

\[
M_3
\]

稳定优于更简单模型时，才说明增加记忆/注意状态有数据支持。

---

# 29. 三问统一的训练与验证协议

## 29.1 外层验证先固定

推荐：

\[
\text{Outer CV}
\]

用于最终评估。

内层：

\[
\text{Inner CV}
\]

用于选择：

- 滤波范围；
- 小波阈值；
- 低秩阶数；
- 正则系数；
- 神经场阶数；
- 认知模型超参数。

---

## 29.2 防止 trial 泄漏

同一 trial 的所有时间窗必须在同一个 fold。

错误做法：

```text
trial 1 的 0–300 ms → train
trial 1 的 300–600 ms → test
```

正确做法：

```text
trial 1 → 全部 train
trial 2 → 全部 test
```

---

## 29.3 防止滤波跨边界泄漏

如果先对整段连续记录使用非因果零相位滤波，再按照训练/测试切段，测试未来数据可能通过滤波器参与训练时点的波形计算。

因此预测实验需要：

- 先切分；
- 或使用严格前缀处理；
- 或采用因果滤波。

离线 ERP 回顾性分析可以单独报告，不要和实时预测混在一起。

---

# 30. 推荐模型组合

最终推荐：

## 问题一

**主模型：**

> 带质量掩码、试次变化和潜伏期约束的结构化稳健分解

**基线：**

> 温和滤波 + SURE 小波 + 稳健 ERP + 样条拟合

理由：

- 可以直接回应“保特征降噪”；
- 利用重复 trial 弥补只有三通道的问题；
- 参数仍然可控。

---

## 问题二

**主模型：**

> Gabor—构型编码 + 低阶空间 Wilson–Cowan 神经场 + 有效头皮投影 + 生成式左右证据

**基线：**

> 低维 Wilson–Cowan 神经群 + 线性 lead field

理由：

- 题目特别强调“形状”和“神经元空间分布”；
- 低阶空间模型比直接堆 DCM、Fokker–Planck、Kuramoto 更可验证；
- 三通道条件下必须限制自由度。

---

## 问题三

**主模型：**

> 任务门控的感觉—记忆反馈动力学 + 目标后证据累积 + EEG/RT 联合拟合

**基线：**

> 感觉—保持—比较三阶段状态空间模型

理由：

- 能继承第二问；
- 可以解释两种任务差别；
- 可自然连接 EEG 与反应时。

---

# 31. 一些“高级方法”应如何取舍

方法，包括：

- ICA；
- HHT；
- DCM；
- Fokker–Planck；
- Kuramoto；
- sLORETA；
- 分层贝叶斯；
- 粒子滤波；
- Granger；
- 深度模型等。

这些不应全部堆进最终论文。

更稳妥的原则是：

\[
\boxed{
\text{模型复杂度}
\le
\text{数据能够支持的复杂度}
}
\]

本题只有 F3/Fz/F4 三个头皮通道，因此：

### 可以用

- Wilson–Cowan；
- 低阶神经场；
- 低维状态空间；
- DDM/首次通过时间；
- 受约束投影；
- 简单判别器做验证。

### 谨慎用

- ICA：只有 3 通道；
- DCM：参数较多；
- sLORETA：空间采样不足；
- 高维全脑 Kuramoto；
- 高维深度网络。

这些可以放在补充实验，但不宜成为无法辨识的主模型。

---

# 32. 推荐论文结构

## 第一章：问题重述

概括：

- 视觉刺激；
- EEG；
- 三个建模任务。

---

## 第二章：符号与数据说明

给出：

- 通道；
- 事件；
- 采样率；
- 质量掩码；
- Task-1 / Task-2。

---

## 第三章：数据审计与统一验证框架

重点：

- TgtAct 编码差异；
- \(\pm1000\) 限幅；
- CV 划分；
- 数据泄漏控制。

这一章很值得单独写，因为它体现了你们不是机械套模型。

---

## 第四章：问题一

结构：

1. 原始 EEG 模型；
2. 质量控制；
3. 基线降噪；
4. 结构化保特征分解；
5. ERP/时频特征；
6. 曲线拟合；
7. 半模拟恢复；
8. 留出验证；
9. 消融。

---

## 第五章：问题二

结构：

1. 视觉形状编码；
2. LGN；
3. V1 Gabor；
4. 构型编码；
5. Wilson–Cowan；
6. 神经场降阶；
7. EEG forward model；
8. 参数估计；
9. 左右生成证据；
10. 消融与反事实。

---

## 第六章：问题三

结构：

1. trial 时间线；
2. 感觉状态；
3. 记忆状态；
4. 注意门控；
5. 比较状态；
6. DDM；
7. EEG/RT 联合似然；
8. 竞争模型；
9. 固定前缀预测；
10. 错误/漏答处理。

---

## 第七章：模型评价

分别总结：

- 保真性；
- 稳定性；
- 泛化性；
- 可解释性；
- 参数可辨识性。

---

## 第八章：优缺点与推广

重点承认：

- 三通道空间分辨率有限；
- 没有个体 MRI；
- 海马只能作为潜在功能状态解释；
- A、B 身份未确认前不能做强“跨受试者”结论。

---

# 33. 建议输出图表

## 问题一

1. 三通道原始 EEG 片段；
2. 质量掩码/限幅分布；
3. PSD；
4. 原始 vs 去噪 ERP；
5. 左右 cue ERP；
6. F4−F3 差分；
7. ERP spline fit；
8. CWT；
9. ITPC；
10. 模拟伪影恢复图；
11. 分类混淆矩阵；
12. 消融结果。

---

## 问题二

1. 左右三角形参数化输入；
2. LGN DoG 响应；
3. Gabor 方向图；
4. 构型编码图；
5. 神经场活动模式；
6. \(E(t),I(t)\)；
7. source current；
8. 模拟 EEG vs 真实 ERP；
9. 左右机制特征；
10. 生成似然比；
11. 参数灵敏度；
12. 空间消融。

---

## 问题三

1. 完整 trial 时间线；
2. 感觉/记忆/比较状态；
3. Task-1 vs Task-2；
4. EEG 拟合；
5. 决策变量轨迹；
6. RT 分布；
7. 固定前缀 RT 预测；
8. 竞争模型性能；
9. 去记忆/去注意消融。

---

# 34. 建议最终结果表

## 表 1：数据质量

| record | cue 数 | 左/右 | 饱和比例 | 丢弃 trial | 有效 trial |
|---|---:|---:|---:|---:|---:|

## 表 2：ERP

| task | cue | electrode | mean amp | peak amp | latency | AUC |
|---|---|---|---:|---:|---:|---:|

## 表 3：问题一方法对比

| method | baseline noise | recovery error | latency error | left/right CV |
|---|---:|---:|---:|---:|

## 表 4：问题二模型

| model | EEG RMSE | NLL | left/right decoding | parameter stability |
|---|---:|---:|---:|---:|

## 表 5：问题三

| model | EEG RMSE | RT MAE | RT NLL | complexity |
|---|---:|---:|---:|---:|

---

# 35. 代码实现建议

推荐目录：

```text
C_EEG/
├── data/
├── configs/
│   ├── preprocess.yaml
│   ├── model_q2.yaml
│   └── model_q3.yaml
├── src/
│   ├── io/
│   │   ├── load_mat.py
│   │   └── events.py
│   ├── preprocessing/
│   │   ├── quality.py
│   │   ├── filters.py
│   │   ├── wavelet.py
│   │   └── structured_denoise.py
│   ├── features/
│   │   ├── erp.py
│   │   ├── timefreq.py
│   │   └── spatial.py
│   ├── visual/
│   │   ├── stimulus.py
│   │   ├── dog.py
│   │   └── gabor_config.py
│   ├── neural/
│   │   ├── wilson_cowan.py
│   │   ├── neural_field.py
│   │   └── forward_eeg.py
│   ├── cognition/
│   │   ├── state_space.py
│   │   ├── memory.py
│   │   └── ddm.py
│   ├── evaluation/
│   │   ├── cv.py
│   │   ├── metrics.py
│   │   ├── simulation.py
│   │   └── ablation.py
│   └── plots/
├── scripts/
│   ├── 01_audit_data.py
│   ├── 02_question1.py
│   ├── 03_question2.py
│   ├── 04_question3.py
│   └── 05_make_figures.py
└── results/
```

---

# 36. 实际实施顺序

## 阶段 A：数据审计

先完成：

- 文件读取；
- 通道核验；
- event table；
- TgtAct 解析；
- 限幅检查；
- PSD；
- trial 划分。

**这一步完成前不要直接训练模型。**

---

## 阶段 B：问题一 baseline

先完成：

\[
\text{filter}
+
\text{baseline}
+
\text{artifact rejection}
+
\text{ERP}
\]

先确保数据流程正确。

---

## 阶段 C：问题一高级模型

实现：

\[
X=L+V+A+R
\]

再做：

- simulation recovery；
- information preservation；
- ablation。

---

## 阶段 D：问题二最简生成模型

先做：

\[
\text{Gabor}
\rightarrow
\text{Wilson-Cowan}
\rightarrow
Lq
\]

确认模型可以拟合/预测 EEG。

---

## 阶段 E：加入空间模式

再扩展：

\[
\text{Wilson-Cowan}
\rightarrow
\text{low-order neural field}
\]

如果留出预测没有稳定收益，应保留最简模型，而不是为了“高级”硬上复杂模型。

---

## 阶段 F：问题三

先做状态空间：

\[
S-M-C
\]

再加 DDM。

不要一开始就同时实现：

- 粒子滤波；
- MCMC；
- DCM；
- Kuramoto；
- 全贝叶斯层次模型。

---

# 37. 最值得写成论文创新点的内容

综合两份材料，真正有题目针对性的创新点不是“用了某个很新的算法”，而是以下三点。

## 创新点 1：保留 trial 变化的结构化去噪

不是：

\[
EEG=\text{signal}+\text{noise}
\]

而是：

\[
EEG=
\text{共同视觉响应}
+
\text{真实试次变化}
+
\text{结构化伪影}
+
\text{背景活动}
\]

这直接回答“去噪同时保留视觉形状信息”。

---

## 创新点 2：形状空间构型进入神经动力学

建立：

\[
\text{Triangle geometry}
\rightarrow
\text{Gabor/configuration}
\rightarrow
\text{neural field}
\rightarrow
\text{EEG}
\]

而不是单纯：

\[
\text{left/right label}
\rightarrow
\text{classifier}
\]

这直接对应题目图 9 的构型选择性启示。

---

## 创新点 3：同一个潜在认知状态解释 EEG 和反应时间

建立：

\[
\text{sensory/memory state}
\rightarrow
\begin{cases}
EEG\\
decision\ evidence\\
RT
\end{cases}
\]

这会把三问真正连接起来。

---

# 38. 主要雷区

## 38.1 黑箱分类器替代计算模型

CNN/SVM 可以做验证，但不能成为问题二、三的主回答。

---

## 38.2 直接使用 Decon

违反题目核心要求。

---

## 38.3 预设 Task-2 P300 更大

前期版本有这一推测，但后期版本明确建议不要作为约束。

---

## 38.4 把左指向三角形当左视野刺激

两者不是同一个概念。

---

## 38.5 声称恢复海马信号

三通道额区 EEG 不能支撑这种强结论。

应写：

> “模型中的记忆潜在状态具有海马参与的功能解释。”

---

## 38.6 过拟合三通道数据

不要同时估计大量：

- 源位置；
- 全连接矩阵；
- 传导时延；
- lead field；
- 多脑区频率；
- 每个 trial 单独参数。

需要共享参数和强约束。

---

## 38.7 数据泄漏

尤其注意：

- ERP template；
- denoising dictionary；
- normalization；
- feature selection；
- latency template；

全部只能在训练数据估计。

---

# 39. 一套最现实的最终版本

如果竞赛时间有限，最推荐以下组合。

## 第一问

```text
数据审计
→ 温和带通
→ 限幅/异常 mask
→ SURE wavelet baseline
→ Structured robust decomposition
→ Weighted ERP
→ spline fit
→ CWT + ITPC
→ half-simulation validation
→ LDA information probe
```

---

## 第二问

```text
Triangle image
→ DoG / LGN
→ Gabor orientation
→ configuration feature
→ 4~8 state Wilson-Cowan / low-order neural field
→ synaptic kernel
→ 3-channel effective lead field
→ fit ERP
→ generative likelihood ratio
```

---

## 第三问

```text
sensory state
+
memory state
+
attention gate
+
comparison state
→ EEG observation
→ target-onset evidence accumulation
→ RT
→ EEG + RT joint fitting
```

这是在**理论深度、实现难度、数据支撑能力**之间最平衡的路线。

---

# 40. 最终结论

两份材料共同指向的最重要结论是：

C 题不能被做成三个孤立问题，更不能被简化成“EEG 滤波 + 分类”。

完整的建模闭环应是：

\[
\boxed{
\text{数据质量控制}
}
\]

\[
\Downarrow
\]

\[
\boxed{
\text{保留视觉形状特征的 EEG 去噪}
}
\]

\[
\Downarrow
\]

\[
\boxed{
\text{可靠的单试次与 ERP 响应}
}
\]

\[
\Downarrow
\]

\[
\boxed{
\text{视觉形状构型}
\rightarrow
\text{神经动力学}
}
\]

\[
\Downarrow
\]

\[
\boxed{
\text{有效脑源}
\rightarrow
\text{F3/Fz/F4 EEG}
}
\]

\[
\Downarrow
\]

\[
\boxed{
\text{感觉}
+
\text{记忆}
+
\text{注意}
+
\text{比较}
+
\text{决策}
}
\]

\[
\Downarrow
\]

\[
\boxed{
\text{脑电预测}
+
\text{反应时间预测}
}
\]

从比赛论文角度看，全文最有价值的不是模型名称的数量，而是：

1. **问题一证明“去噪没有制造或抹掉左右差异”；**
2. **问题二证明“形状空间构型机制确实提高了留出 EEG 的解释/预测能力”；**
3. **问题三证明“增加记忆/注意状态后，既改善 EEG 预测，也改善行为时间预测”；**
4. **三问使用统一数据切分、统一事件定义和统一不确定性处理。**

如果这四点能够真正用附件数据跑出来，论文会形成一个相对完整的“数据—机制—认知”闭环。

---

# 附：两份源材料中应保留的谨慎表述

为避免论文中过度解释，建议保留以下措辞：

- “候选 P300/任务相关正向成分”，而不是仅凭 F3/Fz/F4 就宣称完整观测到经典中央—顶区 P300；
- “有效神经群”“低阶神经场”，而不是声称从三电极恢复真实高分辨率皮层活动；
- “有效头皮投影/lead-field”，而不是个体真实头模型；
- “具有海马/记忆功能解释的潜在状态”，而不是“重建海马脑电”；
- “A、B 两组记录”，在受试者身份没有额外说明前，不轻率写成“两名受试者”；
- “生成式左右刺激证据”，而不是把分类准确率当作神经机制本身。

