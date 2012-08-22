drop table if exists nodes;
create table nodes (
  id integer primary key autoincrement,
  hostname string not null,
  role_id integer not null,
  cluster_id integer not null
);

drop table if exists clusters;
create table clusters (
  id integer primary key autoincrement,
  name string not null,
  description integer not null,
  blob string not null
);

drop table if exists roles;
create table roles (
  id integer primary key autoincrement,
  name string not null,
  description integer not null,
  map string not null
);
