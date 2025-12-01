INSERT INTO alembic_version VALUES('5a8a153fd90d');

CREATE TABLE "Deposit" (
	id SERIAL PRIMARY KEY, 
	recipient VARCHAR(20) NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	gateway_response TEXT, 
	transaction_type VARCHAR(20) NOT NULL, 
	sim_used VARCHAR(20), 
	service_partner_id VARCHAR(100), 
	partner_id VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
	validated_at TIMESTAMP, 
	updated_at TIMESTAMP, 
	error_message TEXT
);

INSERT INTO "Deposit" VALUES
(1,'623040031',2000,'error', E'\nRequest: 1,*142*1*2000*623040031*1*4102#\r\nResponse: Error\r\nMessage: Send USSD failed, Operation is not supported.\r\n','deposit',NULL,NULL,'637473','2025-11-20 19:40:10.249467',NULL,'2025-11-20 19:40:14','No confirmation menu received'),
(2,'623040031',2000,'failed', E'\nRequest: 1,*142*1*2000*623040031*1*4102#\r\nResponse: Error\r\nMessage: Send USSD failed, Operation is not supported.\r\n','deposit',NULL,NULL,'637473','2025-11-20 19:44:27.972329',NULL,'2025-11-20 19:44:32','No confirmation menu received'),
(3,'623040031',2000,'pending', E'\nRequest: 2,*142*1*2000*623040031*1*4102#\r\nResponse: Success\r\nMessage: Vous allez déposer 2000 GNF pour le client 623040031\n1.Confirmer\n\n9.Accueil\n0.Prec\r\n','deposit',NULL,NULL,'637473','2025-11-20 19:48:21.741481',NULL,'2025-11-20 19:48:32',NULL),
(4,'623040031',2000,'failed', E'\nRequest: 1,*142*1*2000*623040031*1*4102#\r\nResponse: Error\r\nMessage: Send USSD failed, Operation is not supported.\r\n','deposit',NULL,NULL,'637473','2025-11-20 20:02:32.254230',NULL,'2025-11-20 20:02:36','No confirmation menu received'),
(5,'623040031',2000,'success','Depot vers 623040031 reussi. Montant 2000.00GNF, Frais 0.00GNF, Commission 0.00GNF, ID Transaction: CI251122.1117.C88102, Nouveau Solde 107500.07GNF.','deposit',NULL,'CI251122.1117.C88102','637473','2025-11-20 20:02:56.494370','2025-11-22 11:46:05.542300','2025-11-22 11:46:05',NULL);

-- Repeat the same for other Deposit inserts, just remove replace(...) and wrap multi-line text in E''

CREATE TABLE withdrawals (
	id SERIAL PRIMARY KEY, 
	amount NUMERIC(10, 2) NOT NULL, 
	sender VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	gateway_response TEXT, 
	sim_used VARCHAR(20), 
	transaction_type VARCHAR(20) NOT NULL, 
	service_partner_id VARCHAR(100), 
	partner_id VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
	validated_at TIMESTAMP, 
	updated_at TIMESTAMP, 
	error_message TEXT
);

-- Example insert:
INSERT INTO withdrawals VALUES
(1,2000,'623040031','success','Retrait de 623040031 effectue. Montant 2000.00GNF, Frais 0.00GNF, Commission 0.00GNF, ID Transaction: CO251120.1646.D14897, Nouveau Solde 105500.07GNF.',NULL,'withdrawal','CO251120.1646.D14897','3884843','2025-11-20 16:29:25.695121','2025-11-21 14:04:22.483345','2025-11-21 14:04:22',NULL);

CREATE TABLE airtimes (
	id SERIAL PRIMARY KEY, 
	recipient VARCHAR(20) NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	gateway_response TEXT, 
	sim_used VARCHAR(20), 
	transaction_type VARCHAR(20) NOT NULL, 
	service_partner_id VARCHAR(100), 
	partner_id VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
	validated_at TIMESTAMP, 
	updated_at TIMESTAMP, 
	error_message TEXT
);

CREATE TABLE email_messages (
	id SERIAL PRIMARY KEY, 
	gmail_account VARCHAR, 
	message_id VARCHAR, 
	subject VARCHAR, 
	sender VARCHAR, 
	body TEXT NOT NULL, 
	received_at TIMESTAMP, 
	parsed_transaction_id VARCHAR, 
	matched BOOLEAN
);

-- Example email_messages insert
INSERT INTO email_messages VALUES
(1,'withdrawal','19aa273cba1d56d2','Withdrawal','john nash <nashjohnforbes30@gmail.com>','Retrait de 623040031 effectue. Montant 2000.00GNF, Frais 0.00GNF, Commission 0.00GNF, ID Transaction: CO251120.1646.D14897, Nouveau Solde 105500.07GNF.','2025-11-20 19:15:22.577146',NULL,FALSE);

-- Indexes
CREATE INDEX ix_Deposit_id ON "Deposit" (id);
CREATE INDEX ix_withdrawals_id ON withdrawals (id);
CREATE INDEX ix_airtimes_id ON airtimes (id);
CREATE UNIQUE INDEX ix_email_messages_message_id ON email_messages (message_id);
CREATE INDEX ix_email_messages_gmail_account ON email_messages (gmail_account);
CREATE INDEX ix_email_messages_parsed_transaction_id ON email_messages (parsed_transaction_id);
CREATE INDEX ix_email_messages_id ON email_messages (id);

COMMIT;
