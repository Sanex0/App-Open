-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

CREATE SCHEMA IF NOT EXISTS `sistemas` DEFAULT CHARACTER SET utf8mb4 ;
USE `sistemas` ;

-- -----------------------------------------------------
-- Table `sistemas`.`vta_club`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`vta_club` (
  `id_club` INT NOT NULL,
  `nom_club` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`id_club`))
ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `sistemas`.`vta_cajas`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`vta_cajas` (
  `id_caja` INT NOT NULL AUTO_INCREMENT,
  `detalle_caja` VARCHAR(45) NULL,
  `vta_club_id_club` INT NOT NULL,
  PRIMARY KEY (`id_caja`),
  INDEX `fk_vta_cajas_vta_club1_idx` (`vta_club_id_club` ASC),
  CONSTRAINT `fk_vta_cajas_vta_club1`
    FOREIGN KEY (`vta_club_id_club`)
    REFERENCES `sistemas`.`vta_club` (`id_club`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
AUTO_INCREMENT = 6
DEFAULT CHARACTER SET = latin1
COLLATE = latin1_swedish_ci;

-- -----------------------------------------------------
-- Table `sistemas`.`adrecrear_usuarios`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`adrecrear_usuarios` (
  `id_usuario` INT NOT NULL AUTO_INCREMENT,
  `email_usuario` VARCHAR(500) CHARACTER SET 'utf8mb4' NULL DEFAULT NULL unique, -- CAMBIADO A utf8mb4
  `nombre_usuario` VARCHAR(300) CHARACTER SET 'utf8mb4' NOT NULL, -- CAMBIADO A utf8mb4
  `clave_usuario` TEXT CHARACTER SET 'utf8mb4' NOT NULL, -- CAMBIADO A utf8mb4
  `estado_usuario` TINYINT(1) NOT NULL,
  PRIMARY KEY (`id_usuario`))
ENGINE = InnoDB
AUTO_INCREMENT = 40;

-- -----------------------------------------------------
-- Table `sistemas`.`vta_apertura`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`vta_apertura` (
  `id_apertura` INT NOT NULL AUTO_INCREMENT,
  `estado_apertura` TINYINT NOT NULL DEFAULT 1,
  `fecha_inicio_apertura` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `fecha_termino_apertura` DATETIME NULL DEFAULT NULL,
  `id_caja_fk` INT NOT NULL,
  `id_usuario_fk` INT NOT NULL,
  PRIMARY KEY (`id_apertura`),
  INDEX `fk_vta_apertura_vta_cajas1_idx` (`id_caja_fk` ASC),
  INDEX `fk_vta_apertura_adrecrear_usuarios1_idx` (`id_usuario_fk` ASC) ,
  CONSTRAINT `fk_vta_apertura_vta_cajas1`
    FOREIGN KEY (`id_caja_fk`)
    REFERENCES `sistemas`.`vta_cajas` (`id_caja`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_vta_apertura_adrecrear_usuarios1`
    FOREIGN KEY (`id_usuario_fk`)
    REFERENCES `sistemas`.`adrecrear_usuarios` (`id_usuario`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `sistemas`.`vta_clientes` (MOVIDO ANTES DE VENTAS)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`vta_clientes` (
  `id_cliente` INT NOT NULL AUTO_INCREMENT,
  `email_cliente` VARCHAR(100),
  `nombre_cliente` VARCHAR(10) NOT NULL,
  `telefono_cliente` VARCHAR(16) NULL,
  PRIMARY KEY (`id_cliente`),
  UNIQUE INDEX `email_cliente_UNIQUE` (`email_cliente` ASC))
ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `sistemas`.`vta_ventas`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`vta_ventas` (
  `id_ventas` INT NOT NULL AUTO_INCREMENT,
  `total_ventas` INT NOT NULL,
  `envio_flex` TINYINT NULL DEFAULT 0,
  `envio_fx` TINYINT NULL DEFAULT 0,
  `envio_correo` TINYINT NULL DEFAULT 0,
  `id_apertura` INT NOT NULL,
  `id_cliente_fk` INT NULL, -- NUEVO CAMPO FK
  PRIMARY KEY (`id_ventas`),
  INDEX `fk_vta_ventas_vta_apertura1_idx` (`id_apertura` ASC),
  INDEX `fk_vta_ventas_vta_clientes1_idx` (`id_cliente_fk` ASC), -- NUEVO INDEX
  CONSTRAINT `fk_vta_ventas_vta_apertura1`
    FOREIGN KEY (`id_apertura`)
    REFERENCES `sistemas`.`vta_apertura` (`id_apertura`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_vta_ventas_vta_clientes1` -- NUEVA CONSTRAINT
    FOREIGN KEY (`id_cliente_fk`)
    REFERENCES `sistemas`.`vta_clientes` (`id_cliente`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `sistemas`.`vta_productos`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`vta_productos` (
  `id_prod` INT NOT NULL AUTO_INCREMENT,
  `descripcion_prod` VARCHAR(100) NULL DEFAULT NULL,
  PRIMARY KEY (`id_prod`))
ENGINE = InnoDB
AUTO_INCREMENT = 11
DEFAULT CHARACTER SET = latin1
COLLATE = latin1_swedish_ci;

-- -----------------------------------------------------
-- Table `sistemas`.`vta_detalle_ventas`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`vta_detalle_ventas` (
  `id_detalle_ventas` INT NOT NULL AUTO_INCREMENT,
  `id_listaprecio` INT NOT NULL,
  `cantidad` INT NOT NULL,
  `id_venta` INT NOT NULL,
  `id_producto_fk` INT NOT NULL,
  PRIMARY KEY (`id_detalle_ventas`),
  INDEX `fk_vta_detalle_ventas_vta_productosporcajas1_idx` (`id_producto_fk` ASC),
  INDEX `fk_vta_detalle_ventas_vta_ventas1_idx` (`id_venta` ASC),
  CONSTRAINT `fk_vta_detalle_ventas_vta_productosporcajas1`
    FOREIGN KEY (`id_producto_fk`)
    REFERENCES `sistemas`.`vta_productos` (`id_prod`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_vta_detalle_ventas_vta_ventas1`
    FOREIGN KEY (`id_venta`)
    REFERENCES `sistemas`.`vta_ventas` (`id_ventas`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `sistemas`.`vta_mediopago`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`vta_mediopago` (
  `id_mediopago` INT NOT NULL AUTO_INCREMENT,
  `tipo_pago` VARCHAR(30) NOT NULL,
  `id_ventas_fk` INT NOT NULL,
  PRIMARY KEY (`id_mediopago`),
  INDEX `fk_vta_mediopago_vta_ventas1_idx` (`id_ventas_fk` ASC),
  CONSTRAINT `fk_vta_mediopago_vta_ventas1`
    FOREIGN KEY (`id_ventas_fk`)
    REFERENCES `sistemas`.`vta_ventas` (`id_ventas`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `sistemas`.`vta_permiso_usuarios`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`vta_permiso_usuarios` (
  `id_permiso` INT NOT NULL AUTO_INCREMENT,
  `detalle_permiso` VARCHAR(35) NOT NULL,
  `id_usuario_fk` INT NOT NULL,
  `vta_cajas_id_caja` INT NOT NULL,
  PRIMARY KEY (`id_permiso`),
  INDEX `fk_vta_permiso_usuarios_adrecrear_usuarios_idx` (`id_usuario_fk` ASC) ,
  INDEX `fk_vta_permiso_usuarios_vta_cajas1_idx` (`vta_cajas_id_caja` ASC) ,
  CONSTRAINT `fk_vta_permiso_usuarios_adrecrear_usuarios`
    FOREIGN KEY (`id_usuario_fk`)
    REFERENCES `sistemas`.`adrecrear_usuarios` (`id_usuario`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_vta_permiso_usuarios_vta_cajas1`
    FOREIGN KEY (`vta_cajas_id_caja`)
    REFERENCES `sistemas`.`vta_cajas` (`id_caja`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
AUTO_INCREMENT = 6
DEFAULT CHARACTER SET = latin1
COLLATE = latin1_swedish_ci;

-- -----------------------------------------------------
-- Table `sistemas`.`vta_catalogo_porcaja`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistemas`.`vta_catalogo_porcaja` (
  `id_caja` INT NOT NULL,
  `id_prod` INT NOT NULL,
  PRIMARY KEY (`id_caja`, `id_prod`),
  INDEX `fk_vta_catalogo_cajas_idx` (`id_caja` ASC),
  INDEX `fk_vta_catalogo_productos_idx` (`id_prod` ASC),
  CONSTRAINT `fk_vta_catalogo_productos`
    FOREIGN KEY (`id_prod`)
    REFERENCES `sistemas`.`vta_productos` (`id_prod`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_vta_catalogo_cajas`
    FOREIGN KEY (`id_caja`)
    REFERENCES `sistemas`.`vta_cajas` (`id_caja`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = latin1
COLLATE = latin1_swedish_ci;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;