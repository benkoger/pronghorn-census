UPDATE core.predictions 
SET reviewed_by_user_id = 0 
WHERE pred_id in (
SELECT P.pred_id FROM core.predictions as P
JOIN core.images as I on I.image_id = P.image_id
WHERE P.image_id NOT IN (
	SELECT A.image_id FROM core.annotations as A
	JOIN core.images as I on I.image_id = A.image_id
	WHERE I.survey_id = 3
)
AND P.reviewed_by_user_id != 0 
AND I.survey_id = 3
)

