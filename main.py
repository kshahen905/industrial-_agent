"""
DevOps Log Analyzer - Main Entry Point

Multi-agent system for analyzing DevOps logs and generating solutions.
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import config
from config import get_model_info


def setup_environment():
    """Setup environment and verify necessary components"""
    logger.info("Setting up environment...")

    # ==================== VERIFY OLLAMA ====================
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            logger.info("✓ Ollama is running and accessible")
            # Try to get list of models
            try:
                models_data = response.json()
                if "models" in models_data and models_data["models"]:
                    model_names = [m.get("name", "unknown") for m in models_data["models"][:3]]
                    logger.info(f"  Available models: {', '.join(model_names)}")
                    if len(models_data["models"]) > 3:
                        logger.info(f"  ... and {len(models_data['models']) - 3} more models")
            except:
                pass
        else:
            logger.warning("⚠ Ollama may not be fully ready")
    except Exception as e:
        logger.error(f"✗ Could not connect to Ollama: {e}")
        logger.error("  Please ensure Ollama is running:")
        logger.error("  Windows: ollama serve")
        logger.error("  Then pull a model: ollama pull neural-chat")
        logger.error("")

    # ==================== VERIFY VECTOR DATABASE ====================
    vector_db_path = Path(__file__).parent / "vector_db"
    db_files = list(vector_db_path.glob("*.db")) + list(vector_db_path.glob("*.parquet"))

    if not db_files:
        logger.warning("⚠ Vector database not found. Running ingestion pipeline...")
        ingest_data()
    else:
        logger.info(f"✓ Vector database found ({len(db_files)} files)")
        logger.info(f"  ChromaDB is ready at: {vector_db_path}")

    logger.info("✓ Environment setup complete")


def ingest_data():
    """Run data ingestion pipeline"""
    logger.info("Running data ingestion pipeline...")

    try:
        from ingestion.ingest_data import DataIngestionPipeline

        current_dir = Path(__file__).parent
        docs_path = current_dir / "data" / "docs"
        vector_db_path = current_dir / "vector_db"

        pipeline = DataIngestionPipeline(
            docs_path=str(docs_path),
            vector_db_path=str(vector_db_path),
        )
        pipeline.run()
        logger.info("✓ Data ingestion complete")
    except Exception as e:
        logger.error(f"✗ Data ingestion failed: {e}")
        raise


def initialize_system():
    """Initialize all system components"""
    logger.info("Initializing DevOps Log Analyzer...")

    try:
        # Display model information
        logger.info(get_model_info())

        # Initialize tools
        from tools.tools import initialize_tools
        current_dir = Path(__file__).parent
        vector_db_path = current_dir / "vector_db"
        initialize_tools(str(vector_db_path))
        logger.info("✓ Tools initialized successfully")

        # Initialize agents
        from agents.agents_config import init_agents
        agent_factory = init_agents()
        logger.info("✓ Agents initialized successfully")

        # Create graph
        from graph.multi_agent_graph import create_multi_agent_graph
        graph = create_multi_agent_graph(agent_factory)
        logger.info("✓ Multi-agent graph created successfully")

        return agent_factory, graph

    except Exception as e:
        logger.error(f"✗ System initialization failed: {e}")
        raise


def analyze_log(graph, log_input: str):
    """Analyze a single log message"""
    from graph.multi_agent_graph import run_analysis

    logger.info("\n" + "="*70)
    logger.info("Analyzing log message...")
    logger.info("="*70)

    try:
        result = run_analysis(graph, log_input)
        return result
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return None


def interactive_mode(graph):
    """Interactive mode for analyzing logs"""
    print("\n" + "="*70)
    print("DevOps Log Analyzer - Interactive Mode")
    print("="*70)
    print("\nEnter DevOps log messages for analysis.")
    print("Type 'quit' or 'exit' to exit.\n")

    while True:
        try:
            log_input = input("\n>>> Enter log message: ").strip()

            if log_input.lower() in ['quit', 'exit']:
                print("Exiting...")
                break

            if not log_input:
                print("Please enter a log message.")
                continue

            result = analyze_log(graph, log_input)

            if result:
                print("\n" + result.get("final_output", "No output generated"))

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            continue


def demo_mode(graph):
    """Demo mode with sample logs"""
    print("\n" + "="*70)
    print("DevOps Log Analyzer - Demo Mode")
    print("="*70)

    sample_logs = [
        "ERROR [docker-daemon]: Error response from daemon: driver failed programming external connectivity on endpoint nginx_container (b8c4a7f9d5e8): Error starting userland proxy: listen tcp 0.0.0.0:80: bind: address already in use",
        "Traceback (most recent call last):\n  File \"/home/user/app/main.py\", line 45, in load_config\n    import yaml\nModuleNotFoundError: No module named 'yaml'",
        "ERROR [nginx]: [error] 1234#1234: *567 connect() failed (111: Connection refused) while connecting to upstream, client: 192.168.1.100",
    ]

    for i, log in enumerate(sample_logs, 1):
        print(f"\n{'='*70}")
        print(f"Sample {i}/{len(sample_logs)}")
        print(f"{'='*70}")
        print(f"Log: {log[:100]}...")

        result = analyze_log(graph, log)

        if result:
            print("\n" + result.get("final_output", "No output generated"))

        input("\nPress Enter to continue...")


def main():
    """Main entry point"""
    logger.info("\n" + "="*70)
    logger.info("DevOps Multi-Agent Log Analyzer")
    logger.info("="*70)

    try:
        # Setup
        setup_environment()

        # Initialize
        agent_factory, graph = initialize_system()

        # Determine mode
        if len(sys.argv) > 1:
            if sys.argv[1] == "--demo":
                demo_mode(graph)
            elif sys.argv[1] == "--analyze":
                if len(sys.argv) > 2:
                    log_input = " ".join(sys.argv[2:])
                    result = analyze_log(graph, log_input)
                    if result:
                        print("\n" + result.get("final_output", "No output generated"))
                else:
                    print("Usage: python main.py --analyze '<log message>'")
            else:
                print("Usage:")
                print("  python main.py              # Interactive mode")
                print("  python main.py --demo       # Demo with sample logs")
                print("  python main.py --analyze '<log>'  # Analyze specific log")
        else:
            # Default: interactive mode
            interactive_mode(graph)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
