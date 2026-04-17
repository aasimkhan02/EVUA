<?php
include 'user.php';

$id = $_GET['id'];

$user = getUser($id);

echo "User Name: " . $user['name'];
?>