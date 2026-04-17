"""
AST Visitor Utilities
Provides helper functions for traversing ASTNode trees.
"""
from typing import Callable, Optional

from ..models.migration_models import ASTNode


def find_nodes(root: ASTNode, node_type: str) -> list[ASTNode]:
    """
    Recursively find all nodes of a given type in the AST.

    Parameters
    ----------
    root : ASTNode
        The root node to search from.
    node_type : str
        The node type to match (e.g. "class_declaration", "function_declaration").

    Returns
    -------
    list[ASTNode]
        All matching nodes in depth-first order.
    """
    result: list[ASTNode] = []
    if root.node_type == node_type:
        result.append(root)
    for child in root.children:
        result.extend(find_nodes(child, node_type))
    return result


def find_nodes_matching(
    root: ASTNode,
    predicate: Callable[[ASTNode], bool],
) -> list[ASTNode]:
    """
    Recursively find all nodes for which *predicate* returns True.

    Parameters
    ----------
    root : ASTNode
        The root node to search from.
    predicate : callable
        A function that takes an ASTNode and returns bool.

    Returns
    -------
    list[ASTNode]
        All matching nodes in depth-first order.
    """
    result: list[ASTNode] = []
    if predicate(root):
        result.append(root)
    for child in root.children:
        result.extend(find_nodes_matching(child, predicate))
    return result


def walk(root: ASTNode) -> list[ASTNode]:
    """
    Yield every node in the tree in depth-first order.

    Parameters
    ----------
    root : ASTNode

    Returns
    -------
    list[ASTNode]
    """
    result: list[ASTNode] = [root]
    for child in root.children:
        result.extend(walk(child))
    return result
