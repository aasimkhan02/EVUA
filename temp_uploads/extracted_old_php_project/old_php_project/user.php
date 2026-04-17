<?php
include 'db.php';

function getUser($id) {
    $conn = getConnection();

    $query = "SELECT * FROM users WHERE id = " . $id;
    $result = mysql_query($query);

    if (!$result) {
        die("Query failed: " . mysql_error());
    }

    return mysql_fetch_assoc($result);
}
?>