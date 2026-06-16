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
import tempfile
import subprocess
import shutil
sys.path.append(str(Path(__file__).parent.parent))

from config import GROQ_API_KEY

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
from main import index_codebase

# Page Config
st.set_page_config(
    page_title="CodeSage",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Core Services in Session State
def init_services(api_key: str, repo_url: str):
    with st.spinner("Cloning repository..."):
        temp_dir = tempfile.mkdtemp()
        try:
            subprocess.run(["git", "clone", repo_url, temp_dir], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            st.error(f"Failed to clone repository: {e.stderr.decode()}")
            return False
            
    with st.spinner("Indexing repository (this may take a minute)..."):
        kg, vs, _ = index_codebase(temp_dir, skip_save=True)
        engine = QueryEngine(kg, vs, api_key=api_key)
        impact = ImpactAnalyzer(kg)
        doc_gen = DocGenerator(api_key=api_key)
        refactor = RefactorAgent(api_key=api_key)
        bug_hunter = BugHunterAgent(engine, api_key=api_key)
        
        st.session_state['kg'] = kg
        st.session_state['vs'] = vs
        st.session_state['engine'] = engine
        st.session_state['impact'] = impact
        st.session_state['doc_gen'] = doc_gen
        st.session_state['refactor'] = refactor
        st.session_state['bug_hunter'] = bug_hunter
        st.session_state['repo_url'] = repo_url
        st.session_state['temp_dir'] = temp_dir
        return True

st.title("CodeSage")
st.markdown("AI-powered Codebase Intelligence Platform")

# Sidebar
with st.sidebar:
    st.header("Configuration")
    if not GROQ_API_KEY:
        user_api_key = st.text_input("Groq API Key", type="password", help="Enter your Groq API Key (Free tier works!)")
    else:
        user_api_key = GROQ_API_KEY
        
    repo_url = st.text_input("GitHub Repo URL", placeholder="https://github.com/user/repo")
    
    if st.button("Clone & Analyze", type="primary"):
        if not user_api_key:
            st.error("Please provide a Groq API Key.")
        elif not repo_url:
            st.error("Please provide a GitHub URL.")
        else:
            if init_services(user_api_key, repo_url):
                st.success("Repository loaded successfully!")
    
    st.divider()

if 'kg' not in st.session_state:
    st.info("👈 Please enter your Groq API Key and a GitHub Repository URL in the sidebar to begin.")
    st.stop()

# Retrieve from session state
kg = st.session_state['kg']
vs = st.session_state['vs']
engine = st.session_state['engine']
impact = st.session_state['impact']
doc_gen = st.session_state['doc_gen']
refactor = st.session_state['refactor']
bug_hunter = st.session_state['bug_hunter']

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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💬 Query Codebase", 
    "🕸️ Impact Analysis", 
    "🚨 Code Risk & Complexity",
    "📊 Architecture Graph",
    "📝 AI Auto-Docs",
    "🛠️ Auto-Refactor",
    "🐞 Bug Hunter"
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
    
    def format_impact_target(node_id):
        if node_id == "Select target...": return node_id
        d = kg.graph.nodes[node_id]
        if d.get("type") == "file":
            return f"File: {d.get('path', node_id)}"
        elif d.get("type") in ("function", "method"):
            return f"Function: {d.get('name')} (in {d.get('file', '?')})"
        return str(node_id)
        
    analysis_target = st.selectbox(
        "Select to analyze blast radius:",
        ["Select target..."] + file_nodes + funcs,
        format_func=format_impact_target
    )
    
    if st.button("Calculate Impact", key="btn_impact"):
        if analysis_target != "Select target...":
            with st.spinner("Traversing dependency graph..."):
                target_node_id = analysis_target
                
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
        # Ensure path is absolute relative to temp dir
        file_path = Path(st.session_state['temp_dir']) / selected_file
        
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
                html_dir = Path("data/graph")
                html_dir.mkdir(parents=True, exist_ok=True)
                html_path = str((html_dir / "vis.html").resolve())
                net.save_graph(html_path)
                with open(html_path, "r", encoding="utf-8") as f:
                    components.html(f.read(), height=650)
            except Exception as e:
                st.error(f"Error generating graph: {e}")

# Tab 5: AI Documentation
with tab5:
    st.header("AI Documentation Generator")
    st.markdown("Automatically generate READMEs or function docstrings using the AI model.")
    
    def format_doc_target(node_id):
        if node_id == "Entire Project (README)": return node_id
        d = kg.graph.nodes[node_id]
        return f"Function: {d.get('name')} (in {d.get('file', '?')})"

    doc_target = st.selectbox(
        "Select an item to document:",
        ["Entire Project (README)"] + funcs,
        format_func=format_doc_target
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
                target_node_id = doc_target
                func_node = kg.graph.nodes[target_node_id]
                func_name = func_node.get("name")
                        
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


