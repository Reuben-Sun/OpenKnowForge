---
title: "KL\u6563\u5EA6 KL-Divergence"
tags:
- math
- information-theory
- kl-divergence
created_at: '2026-03-26T12:36:50+00:00'
updated_at: '2026-03-26T12:36:50+00:00'
submitted_at: '2026-03-26T12:36:50+00:00'
date: '2026-03-26'
type: concept
status: published
related: []
---

# KL散度 KL-Divergence

### KL散度

KL散度（Kullback-Leibler Divergence），也称为相对熵（Relative Entropy），用于衡量一个分布相对于另一个分布的相似性。

假设现在有两个离散概率分布 $P$ 和 $Q$，它们的 KL 散度计算公式为：

$$
D_{KL}(P||Q)=\sum_{i}P(i)\log \left(rac{P(i)}{Q(i)} ight)
$$

其中 $P(i)$ 表示分布 $P$ 在第 $i$ 个事件的概率。

特性：

- 非负性：KL 散度通常大于等于 0，当且仅当两个分布相同时等于 0。
- 不对称性：$D_{KL}(P||Q)$ 往往和 $D_{KL}(Q||P)$ 不同。
- 不满足三角不等式：即两边之和大于第三边。
