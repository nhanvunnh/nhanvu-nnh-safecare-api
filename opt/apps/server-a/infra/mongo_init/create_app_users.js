const apps = [
  { dbName: "db_auth", user: "auth_user", passEnv: "AUTH_DB_PASS" },
  { dbName: "db_sms", user: "sms_user", passEnv: "SMS_DB_PASS" },
  { dbName: "db_shop", user: "shop_user", passEnv: "SHOP_DB_PASS" },
  { dbName: "db_laydi", user: "laydi_user", passEnv: "LAYDI_DB_PASS" },
  { dbName: "db_core", user: "core_user", passEnv: "CORE_DB_PASS" },
  { dbName: "db_image", user: "image_user", passEnv: "IMAGE_DB_PASS" },
  { dbName: "db_gnh", user: "gnh_user", passEnv: "GNH_DB_PASS" },
  { dbName: "db_sheet_sync", user: "sheet_sync_user", passEnv: "SHEET_SYNC_DB_PASS" }
];

apps.forEach(({ dbName, user, passEnv }) => {
  const password = process.env[passEnv];
  if (!password) {
    print(`Environment variable ${passEnv} missing. Skip provisioning for ${dbName}.`);
    return;
  }

  const targetDb = db.getSiblingDB(dbName);
  const userDoc = {
    user,
    pwd: password,
    roles: [{ role: "readWrite", db: dbName }]
  };

  try {
    targetDb.createUser(userDoc);
    print(`Created user ${user} for ${dbName}.`);
  } catch (err) {
    if (err.codeName === "DuplicateKey") {
      print(`User ${user} already exists, updating password.`);
      targetDb.updateUser(user, { pwd: password });
    } else {
      throw err;
    }
  }
});
