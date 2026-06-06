import { Router, type IRouter } from "express";
import healthRouter from "./health";
import runsRouter from "./runs";
import branchesRouter from "./branches";

const router: IRouter = Router();

router.use(healthRouter);
router.use(runsRouter);
router.use(branchesRouter);

export default router;
