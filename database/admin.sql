
CREATE TABLE admin(
    id serial primary key, 
    username varchar(50) not null, 
    password varchar(100) not null
); 

INSERT INTO admin (username, password) VALUES ('admin', '123')