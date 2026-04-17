<?php
include 'config.php';

function getConnection() {
    $conn = mysql_connect($GLOBALS['DB_HOST'], $GLOBALS['DB_USER'], $GLOBALS['DB_PASS']);
    if (!$conn) {
        die("Connection failed: " . mysql_error());
    }

    mysql_select_db($GLOBALS['DB_NAME'], $conn);
    return $conn;
}
?>