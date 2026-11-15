INSERT INTO maquina VALUES (1,'PRONTA',0,0);

INSERT INTO ingrediente VALUES
 (1,'AGUA','ml',2000,2000,400), (2,'CAFE','g',500,500,100),
 (3,'LEITE','ml',1000,1000,200), (4,'CHOCOLATE','g',400,400,80),
 (5,'ACUCAR','g',300,300,60),   (6,'COPOS','un',50,50,10);

-- Preços em centavos inteiros: 400 corresponde a R$ 4,00.
INSERT INTO produto (id, nome, preco_centavos, tempo_preparo_s) VALUES
 (1,'Café expresso',400,5), (2,'Café longo',450,8), (3,'Café com leite',600,10),
 (4,'Cappuccino',650,12),   (5,'Chocolate quente',700,12);

INSERT INTO receita_item VALUES
 (1,1,40),(1,2,8),(1,6,1),
 (2,1,120),(2,2,8),(2,6,1),
 (3,1,40),(3,2,8),(3,3,150),(3,6,1),
 (4,1,40),(4,2,8),(4,3,100),(4,4,5),(4,6,1),
 (5,1,50),(5,3,120),(5,4,30),(5,6,1);
