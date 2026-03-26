"""
Streamlit UI Dashboard for CodeSage
"""
import streamlit as st
import os
import networkx as nx
from typing import Dict, Any, List
from pathlib import Path

# Fix relative imports when running from streamlit
import sys
sys.path.append(str(Path(__file__).parent.parent))

from core.knowledge_graph import KnowledgeGraph
from core.embeddings import EmbeddingStore
from core.query_engine import QueryEngine
from core.impact_analyzer import ImpactAnalyzer
from core.complexity import analyze_file_complexity
from core.doc_generator import DocGenerator
import streamlit.components.v1 as components
from pyvis.network import Network
from core.refactor_agent import RefactorAgent
from core.bug_hunter import BugHunterAgent

# Page Config
st.set_page_config(
    page_title="CodeSage",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Core Services in Session State
@st.cache_resource
def init_services():
    kg = KnowledgeGraph()
    kg.load()
    vs = EmbeddingStore()
    vs.load()
    engine = QueryEngine(kg, vs)
    impact = ImpactAnalyzer(kg)
    doc_gen = DocGenerator()
    refactor = RefactorAgent()
    bug_hunter = BugHunterAgent(engine)
    return kg, vs, engine, impact, doc_gen, refactor, bug_hunter

kg, vs, engine, impact, doc_gen, refactor, bug_hunter = init_services()

st.title("CodeSage")
st.markdown("AI-powered Codebase Intelligence")

# Sidebar
with st.sidebar:
    st.header("Project Overview")
    nodes = len(kg.graph.nodes)
    edges = len(kg.graph.edges)
    files = sum(1 for _, data in kg.graph.nodes(data=True) if data.get("type") == "file")
    
    st.metric("Graph Nodes", nodes)
    st.metric("Graph Relationships", edges)
    st.metric("Indexed Files", files)
    st.metric("Vector Blocks", len(vs.metadata))
    
    st.divider()
    
    st.header("File Selector")
    # Get all indexed files
    file_nodes = [node for node, data in kg.graph.nodes(data=True) if data.get("type") == "file"]
    file_names = [kg.graph.nodes[n].get("path", n) for n in file_nodes]
    selected_file = st.selectbox("Select file to analyze", ["None"] + file_names)

# Main Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "💬 Query Codebase", 
    "🕸️ Impact Analysis", 
    "🚨 Code Risk & Complexity",
    "📊 Architecture Graph",
    "📝 AI Auto-Docs",
    "🛠️ Auto-Refactor",
    "🐞 Bug Hunter",
    "🕒 Query History"
])

# Tab 1: Query Codebase
with tab1:
    st.header("Ask Questions about the Codebase")
    st.info("Examples: 'Where is the database connection handled?', 'How does the parser work?', 'What happens when a file changes?'")
    
    query = st.text_input("Enter your question:", key="search_query")
    if st.button("Query", type="primary", use_container_width=True):
        if query:
            with st.spinner("Analyzing graph and embeddings..."):
                response = engine.query(query)
            
            st.markdown("### Answer")
            st.write(response)
            
            # Show debug context
            with st.expander("Show AI Context (Vector Search Results)"):
                results = vs.search(query)
                for i, r in enumerate(results):
                    st.markdown(f"**Match {i+1}** - `{r['filepath']}` (Score: `{r['score']:.4f}`):")
                    st.code(r['text'], language="python")
        else:
            st.warning("Please enter a question.")

# Tab 2: Impact Analysis
with tab2:
    st.header("Impact Analysis")
    st.markdown("Predict what parts of the system break when a file or function is modified.")
    
    # We can select any node. Let's list files and functions.
    funcs = [n for n, d in kg.graph.nodes(data=True) if d.get("type") in ("function", "method")]
    func_names = [kg.graph.nodes[n].get("name", n) for n in funcs]
    
    analysis_target = st.selectbox(
        "Select to analyze blast radius:",
        ["Select target..."] + [f"File: {f}" for f in file_names] + [f"Function: {f}" for f in func_names]
    )
    
    if st.button("Calculate Impact", key="btn_impact"):
        if analysis_target != "Select target...":
            with st.spinner("Traversing dependency graph..."):
                # Parse target
                typ, name = analysis_target.split(": ", 1)
                
                # Find exact node id
                target_node_id = None
                if typ == "File":
                    for n, d in kg.graph.nodes(data=True):
                        if d.get("type") == "file" and d.get("path") == name:
                            target_node_id = n
                            break
                elif typ == "Function":
                    for n, d in kg.graph.nodes(data=True):
                        if d.get("type") in ("function", "method") and d.get("name") == name:
                            target_node_id = n
                            break
                
                if target_node_id:
                    res = impact.analyze_impact(target_node_id, depth=3)
                    
                    st.subheader(f"Risk Level: {res['risk_level']}")
                    st.markdown(res['reasoning'])
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Files Affected", len(res['files_affected']))
                    col2.metric("Functions Affected", len(res['functions_affected']))
                    col3.metric("Classes Affected", len(res['classes_affected']))
                    
                    if res['files_affected']:
                        with st.expander("View Affected Files"):
                            st.write(", ".join(res['files_affected']))
                    if res['functions_affected']:
                        with st.expander("View Affected Functions"):
                            st.write(", ".join(res['functions_affected']))
                else:
                    st.error("Target node not found in graph.")

# Tab 3: Risk & Complexity
with tab3:
    st.header("Code Complexity & Hotspots")
    
    if selected_file != "None":
        st.subheader(f"Analysis for `{selected_file}`")
        # Ensure path is absolute relative to project root
        file_path = Path(__file__).parent.parent / selected_file
        
        if file_path.exists():
            complexities = analyze_file_complexity(str(file_path))
            
            if not complexities:
                st.success("No high-risk functions found in this file! 🚀")
            else:
                for c in complexities:
                    st.markdown("---")
                    color = "red" if c['risk'] == "High" else "orange"
                    st.markdown(f"### <span style='color:{color}'>{c['name']}</span> (Risk: {c['risk']})", unsafe_allow_html=True)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Cyclomatic Complexity", c['complexity'])
                    c2.metric("Lines of Code", c['lines'])
                    c3.metric("Parameters", c['parameters'])
                    
                    if c['issues']:
                        st.markdown("**Issues detected:**")
                        for issue in c['issues']:
                            st.markdown(f"- {issue}")
    else:
        st.info("Please select a file from the sidebar to view complexity metrics.")

# Tab 4: Architecture Graph
with tab4:
    st.header("Interactive Architecture Graph")
    st.markdown("Visualize how files, classes, and functions are connected across your entire project.")
    
    if st.button("Generate Visualization"):
        with st.spinner("Rendering graph..."):
            net = Network(height="600px", width="100%", directed=True, bgcolor="#0E1117", font_color="white")
            
            # Map node types to colors/icons
            color_map = {
                "file": "#E63946",
                "class": "#457B9D",
                "function": "#1D3557",
                "method": "#2A9D8F",
                "module": "#F4A261"
            }
            
            for node, data in kg.graph.nodes(data=True):
                ntype = data.get("type", "unknown")
                color = color_map.get(ntype, "#A8DADC")
                net.add_node(node, label=str(data.get("name", node)), title=f"Type: {ntype}", color=color)
                
            for source, target, data in kg.graph.edges(data=True):
                relation = data.get("relation", "")
                net.add_edge(source, target, title=relation)
                
            # Physics options for better layout
            net.set_options("""
            var options = {
              "physics": {
                "forceAtlas2Based": {
                  "gravitationalConstant": -50,
                  "centralGravity": 0.01,
                  "springLength": 100,
                  "springConstant": 0.08
                },
                "minVelocity": 0.75,
                "solver": "forceAtlas2Based"
              }
            }
            """)
            
            # Save and display
            try:
                html_path = str(Path("data/graph/vis.html").resolve())
                net.save_graph(html_path)
                with open(html_path, "r", encoding="utf-8") as f:
                    components.html(f.read(), height=650)
            except Exception as e:
                st.error(f"Error generating graph: {e}")

# Tab 5: AI Documentation
with tab5:
    st.header("AI Documentation Generator")
    st.markdown("Automatically generate READMEs or function docstrings using the AI model.")
    
    doc_target = st.selectbox(
        "Select an item to document:",
        ["Entire Project (README)"] + [f"Function: {f}" for f in func_names]
    )
    
    if st.button("Generate Docs", type="primary"):
        with st.spinner("Writing documentation..."):
            if doc_target == "Entire Project (README)":
                # Create a structure map
                structure = "Files:\n" + "\n".join(file_names)
                res = doc_gen.generate_readme(structure)
                st.markdown("### Generated README.md")
                st.markdown(res)
                
                with st.expander("Show Raw Markdown"):
                    st.code(res, language="markdown")
            else:
                # Find the function and its code
                func_name = doc_target.split(": ")[1]
                # Try to locate the file line from the graph (naive approach)
                func_node = None
                for n, d in kg.graph.nodes(data=True):
                    if d.get("name") == func_name and d.get("type") in ("function", "method"):
                        func_node = d
                        break
                        
                if func_node and "file" in func_node:
                    st.success(f"Found {func_name} in {func_node['file']} at line {func_node.get('lineno', '?')}.")
                    # Ask LLM to generate docstring based on name + file context
                    context = f"Function {func_name} in {func_node['file']}"
                    res = doc_gen.generate_function_doc(context)
                    st.markdown("### Generated Docstring")
                    st.code(res, language="python")
                else:
                    st.warning("Could not locate the exact code for this function in the graph.")

# Tab 6: Auto-Refactor
with tab6:
    st.header("🛠️ Auto-Refactoring Agent")
    st.markdown("Paste any messy or complex Python block here, and the AI Agent will autonomously rewrite it to be clean, efficient, typed, and well-documented.")
    
    code_input = st.text_area("Paste Python code to refactor:", height=200)
    context_input = st.text_input("Optional context (e.g., 'This is used in the payment pipeline'):")
    
    if st.button("Refactor Code", type="primary"):
        if code_input.strip():
            with st.spinner("Agent is refactoring the code..."):
                res = refactor.refactor_code(code_input, context_input)
                
                col_orig, col_new = st.columns(2)
                with col_orig:
                    st.markdown("#### Original Code")
                    st.code(code_input, language="python")
                with col_new:
                    st.markdown("#### Refactored Code")
                    st.code(res, language="python")
        else:
            st.warning("Please paste some code to refactor.")

# Tab 7: Bug Hunter
with tab7:
    st.header("🐞 Bug Hunter Agent")
    st.markdown("Paste a Python traceback or error directly from your terminal. The agent will autonomously use the vector database to locate the broken file, figure out what went wrong, and write the fix!")
    
    traceback_input = st.text_area("Paste Error/Traceback here:", height=200)
    
    if st.button("Hunt Bug", type="primary"):
        if traceback_input.strip():
            with st.spinner("Hunting down the bug..."):
                res = bug_hunter.hunt_bug(traceback_input)
                st.markdown("### Agent Diagnosis")
                st.write(res)
        else:
            st.warning("Please paste an error traceback.")

# Tab 8: Query History
with tab8:
    st.header("🕒 Query History")
    st.markdown("All questions asked to CodeSage are saved in your local MongoDB database.")
    
    if st.button("Refresh History", key="btn_refresh_history"):
        pass # Streamlit natively refreshes on button click
        
    try:
        from db.database import get_recent_chat_history
        history = get_recent_chat_history(limit=50)
        
        if not history:
            st.info("No query history found in the database. Head over to the Query codebase tab and ask your first question!")
        else:
            for idx, entry in enumerate(history):
                    # Default empty string to avoid KeyError if schema changes early on
                    q = entry.get('question', 'Unknown')
                    m = entry.get('model_used', 'N/A')
                    
                    with st.expander(f"Q: {q}  |  (Model: {m})"):
                        st.markdown("**Answer:**")
                        st.write(entry.get('answer', ''))
                        if 'timestamp' in entry:
                            st.caption(f"Asked on: {entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} UTC")
    except Exception as e:
        st.error(f"Error fetching MongoDB history: {e}")
