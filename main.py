import os
import argparse
from pathlib import Path

from core.parser import ProjectParser
from core.knowledge_graph import KnowledgeGraph
from core.embeddings import EmbeddingStore
from core.watcher import start_watcher

def index_codebase(root_dir: str):
    """Full indexing pipeline: Parse -> Graph -> Embeddings"""
    print(f"Indexing project at: {root_dir}")
    
    # Init
    parser = ProjectParser(root_dir)
    kg = KnowledgeGraph()
    vs = EmbeddingStore()
    
    # 1. Parse Directory
    print("Parsing files via AST...")
    modules = parser.parse_project()
    print(f"Parsed {len(modules)} Python files.")
    
    # 2. Build Knowledge Graph
    print("Building knowledge graph...")
    kg.build_from_modules(modules)
    kg.save()
    print(f"Graph created with {len(kg.graph.nodes)} nodes and {len(kg.graph.edges)} edges.")
    
    # 3. Build Vector Store
    print("Chunking and generating OpenAI embeddings...")
    vs.clear()
    for mod in modules:
        filepath = Path(root_dir) / mod.filepath
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            vs.chunk_and_embed_file(mod.filepath, content)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            
    vs.save()
    print(f"Vector store created with {len(vs.metadata)} chunks.")
    
    print("✅ Indexing Complete!")
    return kg, vs, parser

def main():
    parser = argparse.ArgumentParser(description="CodeSage CLI")
    parser.add_argument("command", choices=["index", "ui", "watch"], help="Command to run")
    parser.add_argument("--dir", default=".", help="Project directory to index")
    
    args = parser.parse_args()
    
    # Always resolve to absolute project directory
    target_dir = str(Path(args.dir).resolve())
    
    if args.command == "index":
        index_codebase(target_dir)
        
    elif args.command == "ui":
        # Check if indexed
        if not (Path("data/index/faiss.index").exists() and Path("data/graph/project_graph.gpickle").exists()):
            print("Project not indexed. Indexing first...")
            index_codebase(target_dir)
            
        print("Starting Streamlit UI...")
        os.system(f"streamlit run ui/app.py")
        
    elif args.command == "watch":
        print("Starting file watcher daemon...")
        kg = KnowledgeGraph()
        kg.load()
        vs = EmbeddingStore()
        vs.load()
        doc_parser = ProjectParser(target_dir)
        
        observer = start_watcher(target_dir, kg, vs, doc_parser)
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

if __name__ == "__main__":
    main()
