from collections import defaultdict

import pandas as pd
import streamlit as st
from graphviz import Digraph

from config import STORES, TERMINALS, WAREHOUSES
from max_flow import Edge, load_edges, solve_logistics_network

st.set_page_config(
    page_title="Retail Logistics Flow",
    layout="wide",
)


def build_custom_edges(default_edges: list[Edge]) -> list[Edge]:
    custom_edges = []

    for edge in default_edges:
        if edge.start in TERMINALS and edge.end in WAREHOUSES:
            new_capacity = st.sidebar.slider(
                f"{edge.start} -> {edge.end}",
                min_value=0,
                max_value=100,
                value=edge.capacity,
                step=5,
            )
            custom_edges.append(Edge(edge.start, edge.end, new_capacity))
        else:
            custom_edges.append(edge)

    return custom_edges


def calculate_edge_flows(augmenting_paths) -> dict[tuple[str, str], int]:
    edge_flows = defaultdict(int)

    for path in augmenting_paths:
        for start, end in zip(path.nodes, path.nodes[1:]):
            edge_flows[(start, end)] += path.flow

    return edge_flows


def build_terminal_store_dataframe(terminal_store_flows) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Термінал": terminal,
                "Магазин": store,
                "Потік": terminal_store_flows[(terminal, store)],
            }
            for terminal in TERMINALS
            for store in STORES
        ]
    )


def build_paths_dataframe(augmenting_paths) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Крок": index,
                "Збільшуючий шлях": " -> ".join(path.nodes),
                "Доданий потік": path.flow,
            }
            for index, path in enumerate(augmenting_paths, start=1)
        ]
    )


def define_edge_status(capacity: int, flow: int) -> str:
    if capacity == 0:
        return "заблоковано"
    if flow == capacity:
        return "насичено"
    if flow > 0:
        return "використовується"
    return "не використовується"


def build_edge_load_dataframe(custom_edges, edge_flows) -> pd.DataFrame:
    rows = []

    for edge in custom_edges:
        flow = edge_flows[(edge.start, edge.end)]
        load = flow / edge.capacity if edge.capacity else 0
        rows.append(
            {
                "Маршрут": f"{edge.start} -> {edge.end}",
                "Потік": flow,
                "Пропускна здатність": edge.capacity,
                "Завантаження": load,
                "Стан": define_edge_status(edge.capacity, flow),
            }
        )

    return pd.DataFrame(rows)


def style_positive_flow(value):
    return "background-color: #dcfce7" if value > 0 else ""


def style_edge_status(value):
    colors = {
        "заблоковано": "background-color: #fee2e2",
        "насичено": "background-color: #fed7aa",
        "використовується": "background-color: #dcfce7",
        "не використовується": "background-color: #f1f5f9",
    }
    return colors.get(value, "")


def add_graph_nodes(dot: Digraph) -> None:
    node_groups = [
        (TERMINALS, "box", "#bfdbfe"),
        (WAREHOUSES, "ellipse", "#fef3c7"),
        (STORES, "ellipse", "#bbf7d0"),
    ]

    for nodes, shape, color in node_groups:
        for node in nodes:
            dot.node(
                node,
                node,
                shape=shape,
                style="filled",
                fillcolor=color,
                fontcolor="black",
                fontname="Arial",
            )


def add_graph_edges(dot: Digraph, custom_edges, edge_flows) -> None:
    for edge in custom_edges:
        flow = edge_flows[(edge.start, edge.end)]
        status = define_edge_status(edge.capacity, flow)
        color = {
            "заблоковано": "#dc2626",
            "насичено": "#ea580c",
            "використовується": "#16a34a",
            "не використовується": "#94a3b8",
        }[status]
        style = "dashed" if status == "заблоковано" else "solid"
        penwidth = "3" if status in {"насичено", "використовується"} else "1.5"

        dot.edge(
            edge.start,
            edge.end,
            label=f"{flow}/{edge.capacity}",
            fontsize="10",
            fontname="Arial",
            color=color,
            fontcolor=color,
            style=style,
            penwidth=penwidth,
        )


def build_network_graph(custom_edges, edge_flows) -> Digraph:
    dot = Digraph()
    dot.attr(rankdir="LR", size="9,5", bgcolor="transparent")
    add_graph_nodes(dot)
    add_graph_edges(dot, custom_edges, edge_flows)
    return dot


def calculate_analysis(max_flow, terminal_store_flows, custom_edges):
    terminal_totals = {terminal: 0 for terminal in TERMINALS}
    store_totals = {store: 0 for store in STORES}

    for (terminal, store), flow in terminal_store_flows.items():
        terminal_totals[terminal] += flow
        store_totals[store] += flow

    max_terminal_flow = max(terminal_totals.values())
    max_terminals = [
        terminal
        for terminal, flow in terminal_totals.items()
        if flow == max_terminal_flow
    ]
    blocked_edges = [edge for edge in custom_edges if edge.capacity == 0]
    positive_capacities = [edge.capacity for edge in custom_edges if edge.capacity > 0]
    min_capacity = min(positive_capacities) if positive_capacities else 0
    min_capacity_edges = [
        edge for edge in custom_edges if min_capacity and edge.capacity == min_capacity
    ]
    min_store_flow = min(store_totals.values())
    min_stores = [
        store for store, flow in store_totals.items() if flow == min_store_flow
    ]

    term_to_wh_cap = sum(
        edge.capacity
        for edge in custom_edges
        if edge.start in TERMINALS and edge.end in WAREHOUSES
    )
    wh_to_store_cap = sum(
        edge.capacity
        for edge in custom_edges
        if edge.start in WAREHOUSES and edge.end in STORES
    )

    return {
        "max_flow": max_flow,
        "terminal_totals": terminal_totals,
        "max_terminals": max_terminals,
        "max_terminal_flow": max_terminal_flow,
        "blocked_edges": blocked_edges,
        "min_capacity": min_capacity,
        "min_capacity_edges": min_capacity_edges,
        "min_store_flow": min_store_flow,
        "min_stores": min_stores,
        "term_to_wh_cap": term_to_wh_cap,
        "wh_to_store_cap": wh_to_store_cap,
    }


def route_list(edges) -> str:
    if not edges:
        return "немає"
    return ", ".join(f"`{edge.start} -> {edge.end}`" for edge in edges)


def render_analysis(analysis) -> None:
    terminal_summary = ", ".join(
        f"`{terminal}`: {flow} од."
        for terminal, flow in analysis["terminal_totals"].items()
    )
    max_terminals = ", ".join(f"`{terminal}`" for terminal in analysis["max_terminals"])
    blocked_summary = route_list(analysis["blocked_edges"])
    min_capacity_summary = route_list(analysis["min_capacity_edges"])
    min_stores = ", ".join(f"`{store}`" for store in analysis["min_stores"])

    if analysis["term_to_wh_cap"] < analysis["wh_to_store_cap"]:
        bottleneck = "`Термінал -> Склад` є головним обмеженням мережі."
    elif analysis["wh_to_store_cap"] < analysis["term_to_wh_cap"]:
        bottleneck = "`Склад -> Магазин` є головним обмеженням мережі."
    else:
        bottleneck = "Сумарні місткості двох рівнів збалансовані."

    st.markdown(f"""
**Поточний максимальний потік: `{analysis["max_flow"]}` одиниць.**

* **Які термінали забезпечують найбільший потік товарів до магазинів?**  
  Найбільший потік забезпечують: {max_terminals} ({analysis["max_terminal_flow"]} од.).
  Розподіл: {terminal_summary}.

* **Які маршрути мають найменшу пропускну здатність і як це впливає на загальний потік?**  
  Заблоковані маршрути з пропускною здатністю `0`: {blocked_summary}.  
  Мінімальна позитивна пропускна здатність: `{analysis["min_capacity"]}` од. на маршрутах {min_capacity_summary}.
  Такі ребра першими обмежують нові збільшуючі шляхи.

* **Які магазини отримали найменше товарів і чи можна збільшити їх постачання?**  
  Найменше товарів ({analysis["min_store_flow"]} од.) отримали: {min_stores}.
  Щоб збільшити їх постачання, треба розширювати маршрути до складів, через які ці магазини обслуговуються.

* **Чи є вузькі місця, які можна усунути для покращення ефективності мережі?**  
  Сумарна пропускна здатність `Термінал -> Склад`: `{analysis["term_to_wh_cap"]}`.
  Сумарна пропускна здатність `Склад -> Магазин`: `{analysis["wh_to_store_cap"]}`.  
  Висновок: {bottleneck}
""")


st.title("Оптимізація логістичної мережі")
st.markdown(
    "Операційна панель для аналізу максимальної пропускної здатності мережі "
    "від терміналів до магазинів через розподільчі склади. "
    "На ребрах графа показано формат `потік/пропускна здатність`."
)

st.sidebar.header("Параметри мережі")
st.sidebar.markdown(
    "Змінюйте пропускну здатність маршрутів від терміналів до складів, "
    "щоб оцінити вплив на загальний потік."
)

default_edges = load_edges()
custom_edges = build_custom_edges(default_edges)

with st.spinner("Обчислення максимального потоку..."):
    result = solve_logistics_network(edges=custom_edges)
    edge_flows = calculate_edge_flows(result.augmenting_paths)

edge_load_df = build_edge_load_dataframe(custom_edges, edge_flows)
terminal_store_df = build_terminal_store_dataframe(result.terminal_store_flows)
paths_df = build_paths_dataframe(result.augmenting_paths)
analysis = calculate_analysis(
    result.max_flow, result.terminal_store_flows, custom_edges
)

saturated_count = int((edge_load_df["Стан"] == "насичено").sum())
blocked_count = int((edge_load_df["Стан"] == "заблоковано").sum())

metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("Максимальний загальний потік", f"{result.max_flow} одиниць")
metric_col2.metric("Насичені маршрути", saturated_count)
metric_col3.metric("Заблоковані маршрути", blocked_count)

col1, col2 = st.columns([1.45, 1])

with col1:
    st.subheader("Схема мережі")
    st.caption(
        "Зелений колір - маршрут використовується, помаранчевий - насичений, "
        "червоний пунктир - заблокований."
    )
    st.graphviz_chart(build_network_graph(custom_edges, edge_flows))

with col2:
    st.subheader("Фактичний потік: термінал -> магазин")
    st.dataframe(
        terminal_store_df.style.map(style_positive_flow, subset=["Потік"]),
        height=460,
        use_container_width=True,
    )

with st.expander("Покроковий розрахунок збільшуючих шляхів", expanded=True):
    if paths_df.empty:
        st.info("Збільшуючих шляхів немає: потік дорівнює 0.")
    else:
        st.dataframe(paths_df, use_container_width=True, hide_index=True)

with st.expander("Завантаження ребер мережі"):
    st.dataframe(
        edge_load_df.style.format({"Завантаження": "{:.0%}"}).map(
            style_edge_status, subset=["Стан"]
        ),
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.subheader("Аналіз результатів")
render_analysis(analysis)
