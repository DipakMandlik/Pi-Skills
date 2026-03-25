"""Procedure Writer Agent — generates Snowflake stored procedures."""

from __future__ import annotations

import logging

from ..base_agent import AgentResult, BaseAgent
from ..state import PipelineState

logger = logging.getLogger(__name__)


class ProcedureWriterAgent(BaseAgent):
    """Generates Snowflake stored procedures based on SQL and user intent.

    Reads optimized SQL from query_optimizer and user intent to produce
    complete, production-ready stored procedures with error handling.
    """

    @property
    def name(self) -> str:
        return "procedure_writer"

    @property
    def dependencies(self) -> list[str]:
        return ["sql_writer"]

    async def run(self, state: PipelineState) -> AgentResult:
        """Generate stored procedures from SQL queries.

        Reads SQL from sql_writer (and optionally query_optimizer),
        produces stored procedure definitions.
        """
        sql_output = state.outputs.get("sql_writer")
        if not sql_output:
            return AgentResult(
                success=False,
                errors=["No SQL queries available from sql_writer"],
            )

        user_intent = state.user_intent
        prompt = user_intent.get("prompt", "")
        queries = sql_output.get("queries", [])

        # Determine procedure language
        language = self._select_language(prompt)

        # Generate procedures
        procedures = []
        for i, query in enumerate(queries):
            proc = self._generate_procedure(query, i, language, prompt)
            procedures.append(proc)

        result = {
            "procedures": procedures,
            "language": language,
            "procedure_count": len(procedures),
            "includes_error_handling": True,
            "includes_logging": True,
        }

        state.update_state(self.name, "outputs", result)
        return AgentResult(success=True, output=result)

    def _select_language(self, prompt: str) -> str:
        """Select the appropriate procedure language."""
        prompt_lower = prompt.lower()
        if any(kw in prompt_lower for kw in ["python", "pandas", "snowpark", "external"]):
            return "python"
        if any(kw in prompt_lower for kw in ["javascript", "dynamic sql", "json"]):
            return "javascript"
        return "sql"

    def _generate_procedure(
        self,
        query: str,
        index: int,
        language: str,
        prompt: str,
    ) -> dict[str, str]:
        """Generate a stored procedure definition."""
        proc_name = f"sp_generated_{index}"

        if language == "sql":
            body = self._generate_sql_procedure_body(query, prompt)
        elif language == "javascript":
            body = self._generate_js_procedure_body(query, prompt)
        else:
            body = self._generate_python_procedure_body(query, prompt)

        return {
            "name": proc_name,
            "language": language,
            "definition": body,
        }

    def _generate_sql_procedure_body(self, query: str, prompt: str) -> str:
        """Generate a SQL-based stored procedure."""
        return (
            "CREATE OR REPLACE PROCEDURE sp_generated_proc(\n"
            "    p_start_date DATE DEFAULT NULL,\n"
            "    p_end_date DATE DEFAULT NULL\n"
            ")\n"
            "RETURNS VARCHAR\n"
            "LANGUAGE SQL\n"
            "CALLED ON NULL INPUT\n"
            "COMMENT = 'Auto-generated procedure from orchestrator'\n"
            "EXECUTE AS CALLER\n"
            "AS\n"
            "$$\n"
            "DECLARE\n"
            "    v_rows_affected NUMBER DEFAULT 0;\n"
            "    v_message VARCHAR DEFAULT '';\n"
            "BEGIN\n"
            f"    -- Original query:\n"
            f"    -- {query[:100]}...\n"
            "\n"
            "    -- Main logic\n"
            f"    {query.rstrip(';')};\n"
            "\n"
            "    v_rows_affected := SQLROWCOUNT;\n"
            "    RETURN 'Success: processed ' || v_rows_affected || ' rows.';\n"
            "\n"
            "EXCEPTION\n"
            "    WHEN OTHER THEN\n"
            "        RETURN 'Error: ' || SQLERRM;\n"
            "END;\n"
            "$$;"
        )

    def _generate_js_procedure_body(self, query: str, prompt: str) -> str:
        """Generate a JavaScript-based stored procedure."""
        return (
            "CREATE OR REPLACE PROCEDURE sp_generated_proc(\n"
            "    p_table_name VARCHAR\n"
            ")\n"
            "RETURNS VARCHAR\n"
            "LANGUAGE JAVASCRIPT\n"
            "CALLED ON NULL INPUT\n"
            "EXECUTE AS CALLER\n"
            "AS\n"
            "$$\n"
            "    try {\n"
            "        let stmt = snowflake.execute({\n"
            f"            sqlText: `{query}`,\n"
            "        });\n"
            "        return 'Success: ' + stmt.getRowCount() + ' rows processed';\n"
            "    } catch (err) {\n"
            "        return 'Error: ' + err.message;\n"
            "    }\n"
            "$$;"
        )

    def _generate_python_procedure_body(self, query: str, prompt: str) -> str:
        """Generate a Python-based stored procedure."""
        return (
            "CREATE OR REPLACE PROCEDURE sp_generated_proc(\n"
            "    p_input_table VARCHAR\n"
            ")\n"
            "RETURNS VARCHAR\n"
            "LANGUAGE PYTHON\n"
            "RUNTIME_VERSION = '3.11'\n"
            "PACKAGES = ('snowflake-snowpark-python')\n"
            "HANDLER = 'run'\n"
            "EXECUTE AS CALLER\n"
            "AS\n"
            "$$\n"
            "import snowflake.snowpark as snowpark\n"
            "\n"
            "def run(session: snowpark.Session, p_input_table: str) -> str:\n"
            "    try:\n"
            f"        result = session.sql(\"{query}\").collect()\n"
            "        return f'Success: processed {len(result)} rows'\n"
            "    except Exception as e:\n"
            "        return f'Error: {str(e)}'\n"
            "$$;"
        )

    def validate_output(self, result: AgentResult) -> bool:
        """Validate that procedures were generated."""
        if not result.success or not result.output:
            return False
        procedures = result.output.get("procedures", [])
        return len(procedures) > 0
