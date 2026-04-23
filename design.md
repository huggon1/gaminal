# Gaminal 终端游戏设计指南

从 bluff-cards 和 fishing 中提炼出来的 UI/UX 原则。
新游戏开发或现有游戏改进时，以此作为参考。

---

## 一、反馈设计

### 核心原则：每个玩家动作都要有即时可见的响应

好的终端游戏里，输入与反馈之间不应有感知延迟。

**颜色传达语义，而非装饰**

| 颜色 | 含义 | 示例 |
|------|------|------|
| 绿色 / 亮绿 | 成功、进展、当前行动者 | fishing 进度条充满、bluff challenge 揭牌是真话 |
| 红色 | 失败、危险、扣血 | fishing 鱼逃跑、bluff 扣血动画 |
| 黄色 | 警告、待决信息、高亮提示 | bluff 的 challenge 动画、最后声明 |
| 青色 (cyan) | 主要可控元素、当前阶段 | fishing 指示器、bluff 当前桌面 rank |
| 暗灰 (dim) | 次要信息、历史记录 | 日志、弃牌堆、等待中的玩家 |

**用特殊字符增强表达力，不要只用文字**

```
♥♥♡  —— 生命值（实心=剩余，空心=已失去）
★★☆☆  —— 难度等级
▶     —— 当前行动者指示
✓ ►   —— 手牌光标与选中状态
█ ░   —— 进度条（比数字更直观）
✦     —— 成功/庆祝特效帧
><> ~o~ ==>  —— 鱼的 ASCII 符号（各有辨识度）
⚡ ★ ⏸  —— 事件标题（challenge、游戏结束、暂停）
```

**多阶段动画用于重要事件**

重要事件不能只更新一次文字，要分阶段展示，给玩家时间理解：

```
bluff challenge 动画（4 阶段，每阶段 0.55s）：
  ⚡ CHALLENGE! ⚡  →  翻牌中...  →  亮出: A A K  →  BLUFF! 扣血
```

动画结束后自动清除，不占用永久空间。  
用 `set_timer(delay, callback)` 实现，不要 `sleep`（会阻塞 UI）。

---

## 二、信息层级设计

### 核心原则：玩家随时知道"现在是什么状态"和"我该做什么"

**信息按重要性分区**

```
┌────────────────────────────────────┐
│           标题栏（固定）             │  最轻量：游戏名
├────────────────────┬───────────────┤
│                    │  实时分数/得分榜│  高频更新但不强调
│   主游戏区（2fr）   │  当前鱼/手牌   │
│   状态 + 动画在这里 │  操作按钮      │
│                    │               │
├────────────────────┴───────────────┤
│           帮助面板（可切换）          │  默认隐藏，? 键打开
├────────────────────────────────────┤
│           状态栏（1 行）             │  当前发生的事 / 错误
└────────────────────────────────────┘
```

布局比例：主区 `2fr`，侧栏 `1fr`，侧栏 `min-width: 24`。

**"当前该做什么"必须始终可见**

界面上始终有一行明确告诉玩家下一步行动：
- `→ Your turn!`
- `Waiting for Bob...`
- `New game in 5s...`
- `Select 1-3 cards and press p`

**状态转换要有视觉锚点**

阶段变化（游戏开始、回合结束、玩家出局）时，用一个醒目的标题行标识当前阶段，而不是让玩家从散乱文字中自己判断。

---

## 三、进度与持续性设计

### 核心原则：玩家要感受到积累感和连续感

**会话内得分持久化**

不要每局重置所有数据。胜场/总分应跨局保留，让玩家感受到成长：

```python
# bluff-cards：游戏结束后自动倒计时重开，得分板不清零
self._game_scores[winner_seat] += 1
# 新局开始时只重置手牌和生命值，不重置 game_scores
```

**连击/奖励系数**

连续成功给额外奖励，让玩家感受到"势头"：

```python
# fishing：连续钓鱼的奖励倍数
bonus = 1 + streak // 3   # 3连=×2, 6连=×3
```

**游戏结束后自动重开，而非强迫退出**

人机游戏里，结束后展示倒计时并自动开始新局：

```
★ GAME OVER ★   New game in 5s...
```

玩家可以继续看得分榜或准备下一局，不用手动重启。

**难度渐进，不要突变**

用阈值表控制难度曲线，平滑过渡：

```python
DIFFICULTY_TABLE = [
    (0,  [0.70, 0.25, 0.05, 0.00]),  # 初期：简单为主
    (10, [0.20, 0.40, 0.30, 0.10]),  # 中期：均衡
    (30, [0.00, 0.00, 0.30, 0.70]),  # 高分：全是强敌
]
```

---

## 四、策略信息透明度

### 核心原则：给玩家足够信息推理，但不剥夺不确定性

**公开总量，隐藏分布**

让玩家知道"总共有多少"，但不知道"谁手里有多少"：

```
bluff-cards 界面显示：
  TABLE RANK: A   [6×A + 2 Jokers = 8 total]
  Pool: 8  You hold: 2  Discard: 0  → others can have at most 6
```

玩家能做基本推理（持牌数 + 弃牌数 → 他人上限），但不能看穿对手。

**显示手牌数量，不显示手牌内容**

```
S2 Bob   ♥♥♥  (4c)   ← 4 张牌，不知道具体是什么
```

**fishing 的类似设计：难度星级**

用星级而非具体数值表示鱼的难度：`★★☆☆` 比 `agility=0.16` 更直观。

---

## 五、AI / Bot 设计

### 核心原则：随机 + 有逻辑，不能让人一眼看穿

**行为要有延迟，让人跟得上**

Bot 之间的出牌间隔 ≥ 1s，否则玩家来不及理解发生了什么：

```python
# 用可配置参数，测试用小值，游戏用大值
bot_delay: float = 1.5   # 生产环境
bot_delay: float = 0.05  # 测试环境（通过参数注入）
```

**概率模型 + 噪声，不要纯规则**

```python
# 挑战概率 = 基础值 + 持牌推理 + 声称张数 + 随机抖动
prob = 0.10
prob += (my_matching / TOTAL_MATCHING) * 0.38  # 信息优势
prob += {1: 0.0, 2: 0.09, 3: 0.22}[claimed_count]  # 声称越多越可疑
prob += rng.uniform(-0.08, 0.08)  # 抖动，避免行为模式化
```

**决定性行为保持强制**

有些行为不能随机，必须确定性处理（否则 AI 显得愚蠢）：

```python
if claimer_hand_count == 0:
    return True  # 必须挑战：对方打出最后一张牌
```

**用 `rng` 参数保持测试确定性**

```python
def should_basic_challenge(..., *, rng: random.Random | None = None) -> bool:
    if rng is None:
        # 确定性旧逻辑（测试用）
        ...
    # 随机新逻辑（游戏用）
    ...
```

---

## 六、Textual 技术模式

### 布局骨架（通用模板）

```python
def compose(self) -> ComposeResult:
    yield Static("游戏名", id="app-title")
    with Horizontal(id="app-body"):
        with Vertical(classes="panel primary-panel"):
            yield Static("", id="main-view", classes="board-text")
        with Vertical(classes="panel side-panel"):
            yield Static("", id="scores-view")   # 得分/统计
            yield Static("", id="info-view")     # 当前状态
            # 按钮或操作区
    yield Static("", id="help-panel")
    yield Static("", id="status-bar")
```

### 帧动画模式

```python
# 多阶段事件动画
stages = ["第一帧文字", "第二帧文字", "第三帧文字"]
self.stage_text = stages[0]
for i, stage in enumerate(stages[1:], 1):
    self.set_timer(0.55 * i, lambda t=stage: self._set_stage(t))
self.set_timer(0.55 * len(stages) + 1.5, self._clear_stage)
```

### 游戏循环模式

```python
# 物理/状态更新循环
self.set_interval(0.05, self.on_tick)   # 20 FPS

def on_tick(self) -> None:
    if self.paused:
        return
    self.game.step()
    self.refresh_view()
```

### 渲染全刷新模式

不要精细控制哪个 widget 更新，直接全部重绘：

```python
def refresh_view(self) -> None:
    self.query_one("#main-view", Static).update(self.render_main())
    self.query_one("#side-view", Static).update(self.render_side())
    self.update_status(self.message)
```

只要 `render_*` 函数足够轻量，20 FPS 全刷新完全不会卡顿。

### 主题切换模式

```python
# CSS 里用类选择器定义两套主题
Screen { background: #0b1020; }          /* modern 默认 */
.theme-stealth { background: black; }   /* stealth 覆盖 */

# 代码里切换
self.remove_class("theme-modern")
self.add_class("theme-stealth")
```

### 服务端 Bot 事件注入（多人游戏）

```python
# 不要在主线程 sleep，用 threading + 事件队列
def _schedule_bot_turn(self) -> None:
    def enqueue():
        self._events.put(("bot_action", None, token))
    threading.Thread(
        target=lambda: (time.sleep(self._bot_delay), enqueue()),
        daemon=True
    ).start()

# 主循环统一处理所有事件（包括 countdown、bot_action 等）
event_type, client_id, payload = events.get()
if event_type == "bot_action":
    self._handle_bot_turn(payload)
```

---

## 七、常见坑和反模式

| 问题 | 错误做法 | 正确做法 |
|------|----------|----------|
| Bot 出牌太快 | `sleep(0.05)` | `sleep(1.5)`，并用参数分离测试/生产 |
| 游戏结束强制退出 | `self.exit(0)` on finish | 倒计时后自动重开，保留得分 |
| 手牌随人数均分 | `cards = deck_size // active_players` | `cards = CARDS_PER_PLAYER`（固定常量） |
| 信息全部堆在一行 | `S1 Alice [online, hand=5, hp=3, out=False]` | 分行 + 图形化（心形 + 箭头） |
| 重要事件只更新文字 | 直接改 message | 多阶段动画 + 延迟清除 |
| AI 行为完全随机 | `random.choice(["challenge", "pass"])` | 概率模型 + 强制条件 + 噪声抖动 |
| 帮助信息常驻显示 | 始终显示控制说明 | 默认隐藏，`?` 键切换 |
| 测试依赖随机行为 | 直接测试概率函数输出 | 用 `rng=None` 走确定性分支，测试分开 |
